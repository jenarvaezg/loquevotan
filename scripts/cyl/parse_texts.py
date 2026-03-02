import argparse
import glob
import json
import os
import re
import unicodedata


DIPUTADOS_FILE = "data/cyl/diputados_raw.json"
SESSIONS_FILE = "data/cyl/sessions_index.json"
TXT_GLOB = "data/cyl/raw/txt/*.txt"
PARSE_STATE_FILE = "data/cyl/parse_state.json"
OUTPUT_PATTERN = "data/cyl/votos_{leg}_raw.json"
LEG_ID_TO_ROMAN = {"11": "XI", "10": "X", "9": "IX", "8": "VIII", "7": "VII"}
LEG_ROMAN_TO_ID = {v: k for k, v in LEG_ID_TO_ROMAN.items()}
PARSER_VERSION = 2


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
    seen_counts = {}
    for vote in all_votations:
        base_id = vote.get("id")
        if not base_id:
            continue
        n = seen_counts.get(base_id, 0) + 1
        seen_counts[base_id] = n
        if n > 1:
            vote["id"] = f"{base_id}-V{n}"

    return all_votations


def main():
    parser = argparse.ArgumentParser(description="Parsea textos de CyL con modo incremental.")
    parser.add_argument("--rebuild", action="store_true", help="Fuerza reprocesado completo de todos los TXT.")
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

    txt_files = sorted(glob.glob(TXT_GLOB))
    seen_files = set()
    skipped = 0
    reparsed = 0

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

        unchanged = (
            not args.rebuild
            and previous_entry.get("signature") == signature
            and all(vote_id in votes_by_id for vote_id in previous_vote_ids)
        )
        if unchanged:
            skipped += 1
            continue

        print(f"Parsing {txt_path}...")
        try:
            parsed_votes = parse_cyl_session(txt_path, diputados_by_leg, session_info)
            for old_vote_id in previous_vote_ids:
                votes_by_id.pop(old_vote_id, None)
            for vote in parsed_votes:
                vote_id = vote.get("id")
                if vote_id:
                    votes_by_id[vote_id] = vote
            state_files[state_key] = {
                "signature": signature,
                "vote_ids": [v.get("id") for v in parsed_votes if v.get("id")],
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

    save_parse_state(state)
    print(
        f"Parse CyL completado: {len(votes_by_id)} votos totales, "
        f"{reparsed} TXT reprocesados, {skipped} TXT reutilizados."
    )


if __name__ == "__main__":
    main()
