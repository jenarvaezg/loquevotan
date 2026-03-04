import argparse
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import unicodedata


DIPUTADOS_FILE = "data/cyl/diputados_raw.json"
SESSIONS_FILE = "data/cyl/sessions_index.json"
TXT_GLOB = "data/cyl/raw/txt/*.txt"
PARSE_STATE_FILE = "data/cyl/parse_state.json"
OUTPUT_PATTERN = "data/cyl/votos_{leg}_raw.json"
AI_PARSE_CACHE_FILE = "data/cyl/ai_parse_cache.json"
LEG_ID_TO_ROMAN = {"11": "XI", "10": "X", "9": "IX", "8": "VIII", "7": "VII"}
LEG_ROMAN_TO_ID = {v: k for k, v in LEG_ID_TO_ROMAN.items()}
PARSER_VERSION = 2
AI_PARSE_VERSION = 1
GENERIC_TITLES = {
    "votación nominal",
    "votacion nominal",
    "votación ordinaria",
    "votacion ordinaria",
    "asunto parlamentario sin clasificar",
}


def normalize_text(text):
    if not text:
        return ""
    text = "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")
    text = text.lower()
    text = re.sub(r"[^a-z0-9 ]", "", text)
    return " ".join(text.split())


def clean_group(group):
    if not group:
        return "Unknown"
    g = group.lower()
    if "popular" in g:
        return "PP"
    if "socialista" in g:
        return "PSOE"
    if "vox" in g:
        return "VOX"
    if "upl" in g:
        return "UPL-SY"
    if "ciudadanos" in g:
        return "CS"
    if "podemos" in g:
        return "PODEMOS"
    if "mixto" in g:
        return "Mixto"
    if "adscrito" in g:
        return "No Adscrito"
    return group


def spanish_to_int(text):
    if not text:
        return 0
    text = text.lower().strip()
    if text.isdigit():
        return int(text)

    units = {
        "cero": 0,
        "un": 1,
        "uno": 1,
        "dos": 2,
        "tres": 3,
        "cuatro": 4,
        "cinco": 5,
        "seis": 6,
        "siete": 7,
        "ocho": 8,
        "nueve": 9,
        "diez": 10,
        "once": 11,
        "doce": 12,
        "trece": 13,
        "catorce": 14,
        "quince": 15,
        "dieciséis": 16,
        "diecisiete": 17,
        "dieciocho": 18,
        "diecinueve": 19,
        "veinte": 20,
        "veintiuno": 21,
        "veintidós": 22,
        "veintitrés": 23,
        "veinticuatro": 24,
        "veinticinco": 25,
        "veintiséis": 26,
        "veintisiete": 27,
        "veintiocho": 28,
        "veintinueve": 29,
        "treinta": 30,
        "cuarenta": 40,
        "cincuenta": 50,
        "sesenta": 60,
        "setenta": 70,
        "ochenta": 80,
        "noventa": 90,
        "una": 1,
        "ninguna": 0,
        "ninguno": 0,
    }
    if text in units:
        return units[text]

    parts = text.split(" y ")
    if len(parts) == 2:
        return units.get(parts[0], 0) + units.get(parts[1], 0)

    return 0


def file_signature(path):
    stat = os.stat(path)
    return f"{stat.st_mtime_ns}:{stat.st_size}"


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r") as f:
        return json.load(f)


def load_ai_parse_cache():
    cache = load_json(AI_PARSE_CACHE_FILE, {})
    if isinstance(cache, dict):
        return cache
    return {}


def save_ai_parse_cache(cache):
    os.makedirs(os.path.dirname(AI_PARSE_CACHE_FILE), exist_ok=True)
    with open(AI_PARSE_CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def clamp_int(value, default=0):
    try:
        n = int(value)
    except Exception:
        return default
    return max(0, n)


def vote_totals_from_nominal(votos):
    favor = sum(1 for v in votos if v.get("voto") == "si")
    contra = sum(1 for v in votos if v.get("voto") == "no")
    abstencion = sum(1 for v in votos if v.get("voto") == "abstencion")
    total = len(votos)
    return {"favor": favor, "contra": contra, "abstencion": abstencion, "total": total}


def canonicalize_vote_id_suffix(raw_suffix, fallback):
    suffix = str(raw_suffix or "").strip()
    if not suffix:
        suffix = fallback
    suffix = suffix.replace("/", "-")
    suffix = re.sub(r"[^A-Za-z0-9\-]", "-", suffix)
    suffix = re.sub(r"-{2,}", "-", suffix).strip("-")
    return suffix.upper() or fallback


def ensure_unique_vote_ids(votes):
    seen_counts = {}
    for vote in votes:
        base_id = vote.get("id")
        if not base_id:
            continue
        n = seen_counts.get(base_id, 0) + 1
        seen_counts[base_id] = n
        if n > 1:
            vote["id"] = f"{base_id}-V{n}"


def normalize_vote_choice(value):
    token = normalize_text(str(value or ""))
    if token in {"si", "sí", "a favor", "favor", "afavor", "1"}:
        return "si"
    if token in {"no", "en contra", "contra", "2"}:
        return "no"
    if token in {"abstencion", "abstención", "abstenerse", "3"}:
        return "abstencion"
    return None


def build_deputy_lookup(diputados_by_leg):
    lookup = {}
    for leg_id, deps in diputados_by_leg.items():
        names = {}
        for d in deps:
            normalized = normalize_text(d.get("nombre"))
            if normalized:
                names[normalized] = d
        lookup[leg_id] = names
    return lookup


def ai_extraction_key(session_info, signature, max_chars, model):
    key_raw = (
        f"{AI_PARSE_VERSION}|{session_info.get('legis_id')}|{session_info.get('pub_num')}|"
        f"{signature}|{max_chars}|{model}"
    )
    return hashlib.sha256(key_raw.encode("utf-8")).hexdigest()


def extract_json_object(raw_text):
    clean = re.sub(r"```json\n?|\n?```", "", raw_text or "").strip()
    if not clean:
        return None
    try:
        parsed = json.loads(clean)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    decoder = json.JSONDecoder()
    for idx, ch in enumerate(clean):
        if ch != "{":
            continue
        try:
            candidate, _ = decoder.raw_decode(clean[idx:])
        except Exception:
            continue
        if isinstance(candidate, dict):
            return candidate
    return None


def extract_ai_context(text, max_chars=22000):
    markers = list(re.finditer(r"Votos emitidos:\s*", text, re.IGNORECASE))
    if not markers:
        return text[:max_chars]
    chunks = []
    budget = max_chars
    for marker in markers:
        start = max(0, marker.start() - 1300)
        end = min(len(text), marker.end() + 900)
        chunk = text[start:end].strip()
        if not chunk:
            continue
        if len(chunk) + 10 > budget:
            chunk = chunk[: max(0, budget - 10)]
        if not chunk:
            break
        chunks.append(chunk)
        budget -= len(chunk) + 10
        if budget <= 250:
            break
    if not chunks:
        return text[:max_chars]
    return "\n\n---\n\n".join(chunks)


def run_gemini_cli_json(prompt_text, model, timeout_seconds):
    cli = shutil.which("gemini")
    if not cli:
        print("  AI fallback skipped: gemini CLI no encontrado.")
        return None

    command = [cli, "-y", "-m", model]
    extensions = os.environ.get("GEMINI_CLI_EXTENSIONS", "conductor").strip()
    if extensions:
        command.extend(["-e", extensions])
    command.extend(["-p", prompt_text])

    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        print(f"  AI fallback timeout (> {timeout_seconds}s).", file=sys.stderr)
        return None
    except Exception as exc:
        print(f"  AI fallback error ejecutando CLI: {exc}", file=sys.stderr)
        return None

    if proc.returncode != 0:
        err = (proc.stderr or "").strip()
        print(f"  AI fallback CLI returned {proc.returncode}: {err[:300]}", file=sys.stderr)
        return None

    payload = extract_json_object(proc.stdout)
    if payload is None:
        snippet = (proc.stdout or "").strip().replace("\n", "\\n")[:280]
        print(f"  AI fallback sin JSON válido. Snippet: {snippet}", file=sys.stderr)
    return payload


def load_parse_state():
    state = load_json(PARSE_STATE_FILE, {"version": PARSER_VERSION, "files": {}})
    if not isinstance(state, dict):
        return {"version": PARSER_VERSION, "files": {}}
    if state.get("version") != PARSER_VERSION:
        # Force full reparse when parser logic changes.
        return {"version": PARSER_VERSION, "files": {}}
    if "files" not in state or not isinstance(state["files"], dict):
        state["files"] = {}
    state["version"] = PARSER_VERSION
    return state


def save_parse_state(state):
    state["version"] = PARSER_VERSION
    with open(PARSE_STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def is_generic_title(title):
    normalized = normalize_text(title)
    return (not normalized) or (normalized in GENERIC_TITLES)


def is_low_confidence_vote(vote):
    title = str(vote.get("titulo", "")).strip()
    if is_generic_title(title):
        return True

    if len(title.split()) <= 3 and vote.get("tipo") != "nominal":
        return True

    tipo = vote.get("tipo")
    if tipo == "ordinaria":
        totals = vote.get("totales") or {}
        total = clamp_int(totals.get("total"))
        has_proponente = bool(str(vote.get("proponente") or "").strip())
        has_votes = bool(vote.get("votos"))
        if total > 0 and not has_proponente and not has_votes:
            return True

    return False


def should_try_ai_fallback(text, parsed_votes):
    if not parsed_votes:
        has_results = bool(re.search(r"Votos emitidos:\s*", text, re.IGNORECASE))
        has_ordinaria_hints = bool(re.search(r"\b(PNL|PL|M|PPL|ACUER|PREA)\b", text))
        return has_results or has_ordinaria_hints

    low_conf_count = sum(1 for vote in parsed_votes if is_low_confidence_vote(vote))
    return low_conf_count >= max(3, int(len(parsed_votes) * 0.6))


def build_ai_extract_prompt(context_text, session_info):
    return (
        "Eres un extractor estructurado de votaciones parlamentarias de Castilla y León.\n"
        "Extrae votaciones SOLO si hay evidencia clara en el texto. No inventes.\n"
        "Devuelve EXCLUSIVAMENTE JSON con esta forma exacta:\n"
        "{\n"
        '  "votaciones": [\n'
        "    {\n"
        '      "id_suffix": "M-000123 o ORD-4 o NOM-2",\n'
        '      "tipo": "ordinaria|nominal",\n'
        '      "titulo": "titulo breve",\n'
        '      "proponente": "grupo o vacio",\n'
        '      "totales": {"favor":0,"contra":0,"abstencion":0,"total":0},\n'
        '      "votos_nominales": [{"diputado":"APELLIDOS NOMBRE","voto":"si|no|abstencion"}]\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "Reglas:\n"
        "- Si no hay votos nominales claros, deja votos_nominales como [].\n"
        "- Para ordinarias sin nominal, rellena totales si existen en texto.\n"
        "- Mantén id_suffix estable y corto.\n"
        "- No incluyas markdown ni explicaciones.\n\n"
        f"Contexto sesión: Legislatura {session_info.get('legis_id')} · Publicación {session_info.get('pub_num')}.\n\n"
        f"TEXTO:\n{context_text}"
    )


def parse_ai_vote_record(record, session_info, dep_lookup_leg, diputados_leg, index):
    if not isinstance(record, dict):
        return None

    leg_id = session_info["legis_id"]
    base_suffix = canonicalize_vote_id_suffix(record.get("id_suffix"), f"AI-ORD-{index + 1}")
    vote_id = f"CYL-{leg_id}-{session_info['pub_num']}-{base_suffix}"
    tipo = str(record.get("tipo") or "ordinaria").strip().lower()
    if tipo not in {"ordinaria", "nominal"}:
        tipo = "ordinaria"

    titulo = str(record.get("titulo") or "").strip()
    if not titulo:
        titulo = "Votación ordinaria" if tipo == "ordinaria" else "Votación nominal"

    proponente = clean_group(str(record.get("proponente") or "").strip())
    if proponente == "Unknown":
        proponente = ""

    votos = []
    for row in record.get("votos_nominales") or []:
        if not isinstance(row, dict):
            continue
        dep_name = str(row.get("diputado") or "").strip()
        vote_choice = normalize_vote_choice(row.get("voto"))
        if not dep_name or not vote_choice:
            continue
        dep_norm = normalize_text(dep_name)
        found = dep_lookup_leg.get(dep_norm)
        votos.append(
            {
                "diputado": found["nombre"] if found else dep_name,
                "diputadoId": found["id"] if found else f"CYL-UNK-{dep_norm[:18]}",
                "grupo": clean_group(found["grupo"]) if found else "Unknown",
                "voto": vote_choice,
            }
        )

    totals_raw = record.get("totales") or {}
    totals = {
        "favor": clamp_int(totals_raw.get("favor")),
        "contra": clamp_int(totals_raw.get("contra")),
        "abstencion": clamp_int(totals_raw.get("abstencion")),
        "total": clamp_int(totals_raw.get("total")),
    }

    if votes := votos:
        nominal_totals = vote_totals_from_nominal(votes)
        if totals["total"] <= 0:
            totals = nominal_totals
    counted = totals["favor"] + totals["contra"] + totals["abstencion"]
    if totals["total"] < counted:
        totals["total"] = counted

    if totals["total"] <= 0 and not votos:
        return None

    vote = {
        "id": vote_id,
        "fecha": session_info["date"],
        "titulo": titulo[:200],
        "votos": votos,
        "tipo": tipo,
        "metadatos": {
            "tipo": "ai_extract",
            "ai_model": os.environ.get("CYL_PARSE_AI_MODEL", "gemini-2.5-flash"),
            "ai_parse_version": AI_PARSE_VERSION,
        },
    }
    if proponente:
        vote["proponente"] = proponente

    if tipo == "ordinaria":
        vote["totales"] = totals
        if totals["favor"] == totals["total"] and totals["total"] > 0 and not votos:
            for dep in diputados_leg:
                vote["votos"].append(
                    {
                        "diputado": dep["nombre"],
                        "diputadoId": dep["id"],
                        "grupo": clean_group(dep["grupo"]),
                        "voto": "si",
                    }
                )
            vote["metadatos"] = {
                "tipo": "deduccion_grupal_ai",
                "nota": "Voto unánime deducido desde extracción IA de resultados agregados.",
                "ai_model": os.environ.get("CYL_PARSE_AI_MODEL", "gemini-2.5-flash"),
                "ai_parse_version": AI_PARSE_VERSION,
            }
    elif totals["total"] > 0 and not vote.get("totales"):
        vote["totales"] = totals

    return vote


def extract_votes_with_ai(file_path, session_info, diputados_by_leg, signature, ai_cache, model, max_chars, timeout_seconds):
    leg_id = session_info["legis_id"]
    cache_key = ai_extraction_key(session_info, signature, max_chars, model)
    cached = ai_cache.get(cache_key)
    if isinstance(cached, dict) and cached.get("version") == AI_PARSE_VERSION:
        return cached.get("votes", [])

    with open(file_path, "r") as f:
        text = f.read()

    context_text = extract_ai_context(text, max_chars=max_chars)
    prompt = build_ai_extract_prompt(context_text, session_info)
    payload = run_gemini_cli_json(prompt, model=model, timeout_seconds=timeout_seconds)
    records = (payload or {}).get("votaciones", [])

    dep_lookup = build_deputy_lookup(diputados_by_leg)
    dep_lookup_leg = dep_lookup.get(leg_id, {})
    diputados_leg = diputados_by_leg.get(leg_id, [])
    votes = []
    for idx, record in enumerate(records):
        vote = parse_ai_vote_record(record, session_info, dep_lookup_leg, diputados_leg, idx)
        if vote:
            votes.append(vote)

    ensure_unique_vote_ids(votes)
    ai_cache[cache_key] = {
        "version": AI_PARSE_VERSION,
        "generated_at": int(time.time()),
        "votes": votes,
    }
    return votes


def merge_votes_with_ai(parsed_votes, ai_votes):
    if not ai_votes:
        return parsed_votes, 0, 0
    if not parsed_votes:
        return ai_votes, len(ai_votes), 0

    by_id = {v.get("id"): v for v in parsed_votes if v.get("id")}
    added = 0
    refined = 0

    for ai_vote in ai_votes:
        ai_id = ai_vote.get("id")
        if not ai_id:
            continue
        current = by_id.get(ai_id)
        if not current:
            parsed_votes.append(ai_vote)
            by_id[ai_id] = ai_vote
            added += 1
            continue

        changed = False
        if is_generic_title(current.get("titulo")) and not is_generic_title(ai_vote.get("titulo")):
            current["titulo"] = ai_vote.get("titulo")
            changed = True
        if not str(current.get("proponente") or "").strip() and str(ai_vote.get("proponente") or "").strip():
            current["proponente"] = ai_vote.get("proponente")
            changed = True
        if not current.get("totales") and ai_vote.get("totales"):
            current["totales"] = ai_vote["totales"]
            changed = True
        if changed:
            refined += 1

    if added or refined:
        print(f"  AI merge: +{added} votos, {refined} refinados.")

    ensure_unique_vote_ids(parsed_votes)
    return parsed_votes, added, refined


def load_existing_votes_map():
    votes_by_id = {}
    for roman in LEG_ID_TO_ROMAN.values():
        path = OUTPUT_PATTERN.format(leg=roman)
        for vote in load_json(path, []):
            vote_id = vote.get("id")
            if vote_id:
                votes_by_id[vote_id] = vote
    return votes_by_id


def split_votes_by_leg(votes_by_id):
    votes_by_leg = {leg_id: [] for leg_id in LEG_ID_TO_ROMAN}
    for vote in votes_by_id.values():
        vote_id = vote.get("id", "")
        parts = vote_id.split("-")
        if len(parts) < 2:
            continue
        leg_id = parts[1]
        if leg_id in votes_by_leg:
            votes_by_leg[leg_id].append(vote)
    for leg_id in votes_by_leg:
        votes_by_leg[leg_id].sort(key=lambda v: v.get("id", ""))
    return votes_by_leg


def parse_cyl_session(file_path, diputados_by_leg, session_info):
    with open(file_path, "r") as f:
        text = f.read()

    text = text.replace("&nbsp;", " ").replace("&nbsp", " ")
    text = text.replace("**", "")
    text = re.sub(r"\n\s*\n", "\n\n", text)

    leg_id = session_info["legis_id"]
    all_votations = []

    calls = list(re.finditer(r"(?:Votación|Votaciones)\s+.*?(?:llamamiento|sorteo)", text, re.DOTALL | re.IGNORECASE))

    for i, match in enumerate(calls):
        start_idx = match.start()
        pre_text = text[max(0, start_idx - 2000):start_idx]

        title = "Votación nominal"
        title_match = re.search(
            r"(?:somete a votación|proceder\s+.*?votación\s+(?:de|a|para))\s+(.*?)(?:\.|\n\n|\s{3,}|\[)",
            pre_text,
            re.DOTALL | re.IGNORECASE,
        )
        if title_match:
            candidate = title_match.group(1).strip()
            candidate = re.sub(r"^(?:la|el|los|las|de|del|a|en)\s+", "", candidate, flags=re.IGNORECASE)
            title = candidate[0].upper() + candidate[1:]

        content_after = text[start_idx:start_idx + 15000]
        end_match = re.search(r"El resultado de la votación es el siguiente", content_after, re.IGNORECASE)
        end_idx = end_match.end() + 1000 if end_match else 5000
        content = content_after[:end_idx]

        results = {
            "id": f"CYL-{leg_id}-{session_info['pub_num']}-NOM-{i + 1}",
            "fecha": session_info["date"],
            "titulo": title[:200],
            "votos": [],
            "tipo": "nominal",
        }

        vote_matches = re.finditer(
            r"(?:EL SEÑOR|LA SEÑORA)\s+([A-Z\sÁÉÍÓÚÑ\-]+):\s*\n\s*(Sí|No|Abstención)\.",
            content,
            re.IGNORECASE,
        )
        found_any = False
        for v_m in vote_matches:
            found_any = True
            raw_name = v_m.group(1).strip()
            sense = v_m.group(2).strip().lower()
            norm_name = normalize_text(raw_name)

            found_deputy = None
            for d in diputados_by_leg.get(leg_id, []):
                if normalize_text(d["nombre"]) == norm_name or norm_name in normalize_text(d["nombre"]):
                    found_deputy = d
                    break

            results["votos"].append(
                {
                    "diputado": found_deputy["nombre"] if found_deputy else raw_name,
                    "diputadoId": found_deputy["id"] if found_deputy else f"CYL-UNK-{normalize_text(raw_name)[:10]}",
                    "grupo": clean_group(found_deputy["grupo"]) if found_deputy else "Unknown",
                    "voto": "si" if sense == "sí" else sense,
                }
            )

        if found_any:
            all_votations.append(results)

    results_pattern = r"Votos emitidos:\s*(.*?)\.\s*A favor:\s*(.*?)\.(?:\s*En contra:\s*(.*?)\.)?(?:\s*Abstención:\s*(.*?)\.)?"
    res_matches = list(re.finditer(results_pattern, text, re.IGNORECASE))

    for i, match in enumerate(res_matches):
        start_idx = match.start()
        pre_context = text[max(0, start_idx - 1500):start_idx]

        id_match = re.search(r"([A-Z]+/\d+)", pre_context)
        ref_id = id_match.group(1) if id_match else f"ORD-{i + 1}"

        proponente = ""
        prop_match = re.search(r"presentada por el (Grupo Parlamentario [^,]+)", pre_context, re.I)
        if prop_match:
            proponente = clean_group(prop_match.group(1))

        title = "Votación ordinaria"
        title_match = re.search(
            r"(?:votamos|votación)\s+.*?\s+(?:la|el|los|las)\s+(.*?)(?:\.|admitida|publicada|consecuencia|\n\n)",
            pre_context,
            re.DOTALL | re.IGNORECASE,
        )
        if title_match:
            title = title_match.group(1).strip()
            title = title[0].upper() + title[1:]

        v_emit = spanish_to_int(match.group(1))
        v_favor = spanish_to_int(match.group(2))
        v_contra = spanish_to_int(match.group(3)) if match.group(3) else 0
        v_abst = spanish_to_int(match.group(4)) if match.group(4) else 0

        if v_emit == 0 and v_favor == 0:
            continue

        if any(v["fecha"] == session_info["date"] and abs(len(v["votos"]) - v_emit) < 2 for v in all_votations if v["tipo"] == "nominal"):
            continue

        results = {
            "id": f"CYL-{leg_id}-{session_info['pub_num']}-{ref_id.replace('/', '-')}",
            "fecha": session_info["date"],
            "titulo": title[:200],
            "votos": [],
            "tipo": "ordinaria",
            "totales": {"favor": v_favor, "contra": v_contra, "abstencion": v_abst, "total": v_emit},
            "proponente": proponente,
        }

        if v_favor == v_emit and v_emit > 0:
            for d in diputados_by_leg.get(leg_id, []):
                results["votos"].append(
                    {
                        "diputado": d["nombre"],
                        "diputadoId": d["id"],
                        "grupo": clean_group(d["grupo"]),
                        "voto": "si",
                    }
                )
            results["metadatos"] = {"tipo": "deduccion_grupal", "nota": "Voto unánime deducido por el resultado de la cámara."}

        all_votations.append(results)

    # Ensure stable unique IDs within the session.
    ensure_unique_vote_ids(all_votations)

    return all_votations


def main():
    parser = argparse.ArgumentParser(description="Parsea textos de CyL con modo incremental.")
    parser.add_argument("--rebuild", action="store_true", help="Fuerza reprocesado completo de todos los TXT.")
    parser.add_argument(
        "--ai-fallback",
        action="store_true",
        help="Activa extracción IA solo en documentos de baja confianza (requiere gemini CLI).",
    )
    parser.add_argument(
        "--ai-model",
        default=os.environ.get("CYL_PARSE_AI_MODEL", "gemini-2.5-flash"),
        help="Modelo Gemini para fallback de parseo (default: env CYL_PARSE_AI_MODEL o gemini-2.5-flash).",
    )
    parser.add_argument(
        "--ai-max-chars",
        type=int,
        default=int(os.environ.get("CYL_PARSE_AI_MAX_CHARS", "22000")),
        help="Máximo de caracteres de contexto por documento para IA.",
    )
    parser.add_argument(
        "--ai-timeout",
        type=int,
        default=int(os.environ.get("CYL_PARSE_AI_TIMEOUT_SECONDS", "180")),
        help="Timeout en segundos por llamada de extracción IA.",
    )
    args = parser.parse_args()

    diputados_list = load_json(DIPUTADOS_FILE, [])
    diputados_by_leg = {}
    for d in diputados_list:
        leg = d["nlegis"]
        if leg not in diputados_by_leg:
            diputados_by_leg[leg] = []
        diputados_by_leg[leg].append(d)

    sessions = load_json(SESSIONS_FILE, [])
    sessions_map = {f"{s['legis_id']}-{s['pub_num']}": s for s in sessions}

    votes_by_id = {} if args.rebuild else load_existing_votes_map()
    state = {"version": PARSER_VERSION, "files": {}} if args.rebuild else load_parse_state()
    state_files = state["files"]
    ai_cache = load_ai_parse_cache() if args.ai_fallback else {}

    txt_files = sorted(glob.glob(TXT_GLOB))
    seen_files = set()
    skipped = 0
    reparsed = 0
    ai_calls = 0
    ai_docs_refined = 0

    for txt_path in txt_files:
        doc_id = os.path.basename(txt_path).replace(".txt", "")
        session_info = sessions_map.get(doc_id)
        if not session_info:
            continue

        state_key = os.path.basename(txt_path)
        seen_files.add(state_key)
        signature = file_signature(txt_path)
        previous_entry = state_files.get(state_key, {})
        previous_vote_ids = previous_entry.get("vote_ids", [])
        ai_state_ok = True
        if args.ai_fallback:
            ai_state_ok = (
                bool(previous_entry.get("ai_fallback"))
                and previous_entry.get("ai_parse_version") == AI_PARSE_VERSION
                and previous_entry.get("ai_status") != "failed"
            )

        unchanged = (
            not args.rebuild
            and previous_entry.get("signature") == signature
            and ai_state_ok
            and all(vote_id in votes_by_id for vote_id in previous_vote_ids)
        )
        if unchanged:
            skipped += 1
            continue

        print(f"Parsing {txt_path}...")
        try:
            parsed_votes = parse_cyl_session(txt_path, diputados_by_leg, session_info)
            ai_status = "not_requested"
            if args.ai_fallback:
                ai_status = "not_needed"
                with open(txt_path, "r") as f:
                    text_content = f.read()
                if should_try_ai_fallback(text_content, parsed_votes):
                    ai_votes = extract_votes_with_ai(
                        txt_path,
                        session_info,
                        diputados_by_leg,
                        signature,
                        ai_cache,
                        model=args.ai_model,
                        max_chars=max(4000, args.ai_max_chars),
                        timeout_seconds=max(30, args.ai_timeout),
                    )
                    ai_calls += 1
                    merged_votes, added_votes, refined_votes = merge_votes_with_ai(parsed_votes, ai_votes)
                    if ai_votes:
                        ai_status = "ok"
                    else:
                        ai_status = "failed"
                    if added_votes or refined_votes:
                        ai_docs_refined += 1
                    parsed_votes = merged_votes

            for old_vote_id in previous_vote_ids:
                votes_by_id.pop(old_vote_id, None)
            for vote in parsed_votes:
                vote_id = vote.get("id")
                if vote_id:
                    votes_by_id[vote_id] = vote
            state_files[state_key] = {
                "signature": signature,
                "vote_ids": [v.get("id") for v in parsed_votes if v.get("id")],
                "ai_fallback": bool(args.ai_fallback),
                "ai_parse_version": AI_PARSE_VERSION if args.ai_fallback else 0,
                "ai_status": ai_status,
            }
            reparsed += 1
            print(f"  Found {len(parsed_votes)} votations")
        except Exception as e:
            print(f"  Error parsing {txt_path}: {e}")

    for stale_key in [k for k in list(state_files.keys()) if k not in seen_files]:
        for old_vote_id in state_files[stale_key].get("vote_ids", []):
            votes_by_id.pop(old_vote_id, None)
        del state_files[stale_key]

    os.makedirs("data/cyl", exist_ok=True)
    votes_by_leg = split_votes_by_leg(votes_by_id)
    for leg_id, roman in LEG_ID_TO_ROMAN.items():
        with open(OUTPUT_PATTERN.format(leg=roman), "w") as f:
            json.dump(votes_by_leg[leg_id], f, indent=2, ensure_ascii=False)

    if args.ai_fallback:
        save_ai_parse_cache(ai_cache)
    save_parse_state(state)
    summary = (
        f"Parse CyL completado: {len(votes_by_id)} votos totales, "
        f"{reparsed} TXT reprocesados, {skipped} TXT reutilizados."
    )
    if args.ai_fallback:
        summary += f" AI fallback: {ai_calls} docs evaluados, {ai_docs_refined} refinados."
    print(summary)


if __name__ == "__main__":
    main()
