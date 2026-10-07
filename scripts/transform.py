#!/usr/bin/env python3
"""
Transforma los JSON brutos del Congreso en los ficheros del frontend.
Usa Gemini AI para categorizar los textos parlamentarios con etiquetas múltiples.

Siempre regenera desde data/raw completo. Para no publicar un dataset recortado
cuando data/raw está incompleto (p.ej. cache de CI perdida), aborta si alguna
legislatura tendría menos votaciones que las ya publicadas (--allow-shrink lo
permite de forma explícita).
"""

import argparse
import glob
import json
import os
import sys
from datetime import datetime, timezone

import ai_utils

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.environ.get("LQV_NATIONAL_RAW_DIR") or os.path.join(SCRIPT_DIR, "..", "data", "raw")
PUBLIC_DIR = os.environ.get("LQV_NATIONAL_PUBLIC_DIR") or os.path.join(SCRIPT_DIR, "..", "public", "data")
CACHE_FILE = os.path.join(SCRIPT_DIR, "..", "data", "cache_categorias.json")
PROMPT_FILE = os.path.join(SCRIPT_DIR, "prompt_categorizacion.txt")
FOTO_MAP_FILE = os.path.join(SCRIPT_DIR, "..", "data", "foto_map.json")
PROVINCIA_MAP_FILE = os.path.join(SCRIPT_DIR, "..", "data", "provincia_map.json")
FEATURED_FILE = os.path.join(SCRIPT_DIR, "..", "data", "featured_votes.json")
MANIFEST_FILE = os.path.join(PUBLIC_DIR, "manifest_home.json")
AMBITOS_FILE = os.path.join(PUBLIC_DIR, "ambitos.json")
META_FILE = os.path.join(PUBLIC_DIR, "votaciones_meta.json")

VOTE_MAP = {
    "Si": "A favor",
    "Sí": "A favor",
    "No": "En contra",
    "Abstención": "Abstención",
}
UNKNOWN_GROUP_TOKENS = {"", "unknown", "desconocido", "null", "none", "n/a", "na"}
ASENTIMIENTO_VALUES = {"sí", "si"}
FALLBACK_TITLE = ai_utils._fallback_categorization()["titulo_ciudadano"]

LEGISLATURAS = [
    {"id": "X", "desde": "2012-01-01", "hasta": "2015-10-27"},
    {"id": "XI", "desde": "2016-01-13", "hasta": "2016-05-03"},
    {"id": "XII", "desde": "2016-07-19", "hasta": "2019-02-13"},
    {"id": "XIII", "desde": "2019-05-21", "hasta": "2019-09-24"},
    {"id": "XIV", "desde": "2020-01-03", "hasta": "2023-05-29"},
    # Cortes disueltas el 2026-10-06 (RD 806/2026); la Diputación Permanente
    # sigue en la XV hasta la sesión constitutiva de la XVI (2026-12-23).
    {"id": "XV", "desde": "2023-08-17", "hasta": "2026-12-22"},
    {"id": "XVI", "desde": "2026-12-23", "hasta": "2099-12-31"},
]
ROMAN_VALUES = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}


def roman_to_int(roman):
    total = 0
    prev = 0
    for ch in reversed(roman.upper()):
        value = ROMAN_VALUES[ch]
        total = total - value if value < prev else total + value
        prev = max(prev, value)
    return total


def get_leg(fecha):
    """Get legislatura ID for a date string (YYYY-MM-DD)."""
    for leg in reversed(LEGISLATURAS):
        if leg["desde"] <= fecha <= leg["hasta"]:
            return leg["id"]
    return ""


def classify_subgrupo(titulo_subgrupo):
    """Classify a tituloSubGrupo into a short type label."""
    if not titulo_subgrupo:
        return ""
    tl = titulo_subgrupo.lower()
    if "texto d" in tl or "conjunto" in tl:
        return "final"
    if "enmienda" in tl:
        return "enmienda"
    if "sección" in tl or "presupuest" in tl:
        return "presupuestos"
    return "otro"


def normalize_group_name(group_name):
    value = (group_name or "").strip()
    if value.lower() in UNKNOWN_GROUP_TOKENS:
        return ""
    return value


def text_hash(text):
    return ai_utils.text_hash(text)


def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    write_json(CACHE_FILE, cache, indent=2)


def write_json(path, payload, indent=None):
    """Write JSON atomically so an interrupted run never leaves a truncated file."""
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        if indent is None:
            json.dump(payload, f, separators=(",", ":"))
        else:
            json.dump(payload, f, ensure_ascii=False, indent=indent)
    os.replace(tmp_path, path)


def parse_congress_date(fecha_str):
    """Convert '26/2/2026' to '2026-02-26'."""
    parts = fecha_str.split("/")
    if len(parts) == 3:
        day, month, year = parts
        return f"{year}-{int(month):02d}-{int(day):02d}"
    return fecha_str


def congress_date_url(leg, fecha):
    """Official opendata page listing every vote of that day (JSON/XML/PDF)."""
    year, month, day = fecha.split("-")
    return (
        "https://www.congreso.es/es/opendata/votaciones"
        f"?targetLegislatura={leg}&targetDate={day}/{month}/{year}"
    )


def tally_votes(data):
    """Count votes and per-group votes for one raw votación.

    Returns (counts, entries, asentimiento) where entries is a list of
    (dip_id, raw_group, code). Votes by assent or secret ballot have no nominal
    list; their counts come from `totales`.
    """
    counts = {"favor": 0, "contra": 0, "abstencion": 0, "no_vota": 0}
    entries = []
    for voto_entry in data.get("votaciones") or []:
        voto = VOTE_MAP.get(voto_entry.get("voto", ""), voto_entry.get("voto", ""))
        if voto == "A favor":
            code = 1
            counts["favor"] += 1
        elif voto == "En contra":
            code = 2
            counts["contra"] += 1
        elif voto == "Abstención":
            code = 3
            counts["abstencion"] += 1
        else:
            code = 4
            counts["no_vota"] += 1
        entries.append((voto_entry.get("diputado"), voto_entry.get("grupo"), code))

    totales = data.get("totales") or {}
    asentimiento = str(totales.get("asentimiento", "")).strip().lower() in ASENTIMIENTO_VALUES
    if not entries and not asentimiento:
        counts["favor"] = _to_int(totales.get("afavor"))
        counts["contra"] = _to_int(totales.get("enContra"))
        counts["abstencion"] = _to_int(totales.get("abstenciones"))
        counts["no_vota"] = _to_int(totales.get("noVotan"))
    return counts, entries, asentimiento


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def vote_result(favor, contra, asentimiento=False):
    if asentimiento:
        return "Aprobada"
    if favor > contra:
        return "Aprobada"
    if contra > favor:
        return "Rechazada"
    return "Empate"


def group_majorities(by_group):
    """Majority position per group, ignoring groups where nobody voted."""
    gm = {}
    for g_name, c in by_group.items():
        if c[1] + c[2] + c[3] == 0:
            continue
        if c[1] >= c[2] and c[1] >= c[3]:
            gm[g_name] = 1
        elif c[2] >= c[3]:
            gm[g_name] = 2
        else:
            gm[g_name] = 3
    return gm


def is_fallback_override(override):
    return override.get("titulo_ciudadano") == FALLBACK_TITLE


def load_existing_overrides():
    """Fields from the currently published files, to keep curated edits."""
    if not os.path.exists(META_FILE):
        return {}, {}

    try:
        with open(META_FILE, "r", encoding="utf-8") as f:
            previous_meta = json.load(f)
    except Exception as e:  # noqa: BLE001
        print(f"WARN: no se pudo leer {META_FILE}: {e}", file=sys.stderr)
        return {}, {}

    previous_categories = previous_meta.get("categorias", [])
    previous_votes = previous_meta.get("votaciones", [])

    previous_detail_by_leg = {}
    for leg in {v.get("legislatura") for v in previous_votes if v.get("legislatura")}:
        votes_path = os.path.join(PUBLIC_DIR, f"votos_{leg}.json")
        if not os.path.exists(votes_path):
            continue
        try:
            with open(votes_path, "r", encoding="utf-8") as f:
                previous_detail_by_leg[leg] = json.load(f).get("detail", {})
        except Exception as e:  # noqa: BLE001
            print(f"WARN: no se pudo leer {votes_path}: {e}", file=sys.stderr)
            previous_detail_by_leg[leg] = {}

    meta_overrides = {}
    detail_overrides = {}

    for idx, vote in enumerate(previous_votes):
        vote_id = vote.get("id")
        if not vote_id:
            continue

        override = {}
        category_idx = vote.get("categoria")
        if isinstance(category_idx, int) and 0 <= category_idx < len(previous_categories):
            override["categoria_label"] = previous_categories[category_idx]
        if isinstance(vote.get("titulo_ciudadano"), str) and vote["titulo_ciudadano"].strip():
            override["titulo_ciudadano"] = vote["titulo_ciudadano"].strip()
        if isinstance(vote.get("etiquetas"), list) and vote["etiquetas"]:
            override["etiquetas"] = vote["etiquetas"]
        if isinstance(vote.get("proponente"), str) and vote["proponente"].strip():
            override["proponente"] = vote["proponente"].strip()
        # A vote published with the "no AI" placeholder is not curated: let a
        # later categorization replace it instead of freezing the placeholder.
        if override and not is_fallback_override(override):
            meta_overrides[vote_id] = override

        leg = vote.get("legislatura")
        detail = previous_detail_by_leg.get(leg, {}).get(str(idx))
        if isinstance(detail, dict) and not is_fallback_override(override):
            detail_override = {}
            for field in ("resumen", "subgrupo", "subgrupo_detalle"):
                value = detail.get(field)
                if isinstance(value, str) and value.strip():
                    detail_override[field] = value.strip()
            if detail_override:
                detail_overrides[vote_id] = detail_override

    return meta_overrides, detail_overrides


def published_counts_by_leg():
    if not os.path.exists(META_FILE):
        return {}
    try:
        with open(META_FILE, "r", encoding="utf-8") as f:
            votes = json.load(f).get("votaciones", [])
    except Exception as e:  # noqa: BLE001
        print(f"WARN: no se pudo leer {META_FILE}: {e}", file=sys.stderr)
        return {}
    counts = {}
    for v in votes:
        leg = v.get("legislatura")
        counts[leg] = counts.get(leg, 0) + 1
    return counts


def find_shrinkage(previous_counts, new_counts):
    """Legislatures that would lose votes compared to the published data."""
    return {
        leg: (prev, new_counts.get(leg, 0))
        for leg, prev in previous_counts.items()
        if new_counts.get(leg, 0) < prev
    }


def sync_ambitos_legislaturas(legs):
    """Keep the national legislature selector in ambitos.json in sync with data."""
    if not os.path.exists(AMBITOS_FILE):
        return
    with open(AMBITOS_FILE, "r", encoding="utf-8") as f:
        ambitos = json.load(f)
    wanted = sorted(legs, key=roman_to_int, reverse=True)
    for ambito in ambitos.get("ambitos", []):
        if ambito.get("id") == "nacional" and ambito.get("legislaturas") != wanted:
            ambito["legislaturas"] = wanted
            write_json(AMBITOS_FILE, ambitos, indent=2)
            print(f"ambitos.json: legislaturas nacionales -> {wanted}")


def raw_file_sort_key(filepath):
    """Chronological order: legislature, date, session, vote number."""
    name = os.path.basename(filepath)
    parts = name[:-5].split("_")  # LXV_20260226_S164_V001
    if name.startswith("L") and len(parts) == 4:
        return (roman_to_int(parts[0][1:]), parts[1], int(parts[2][1:]), int(parts[3][1:]))
    return (0, name, 0, 0)


def list_raw_files():
    # Support both old format (date_S_V.json) and new (Lleg_date_S_V.json)
    files = glob.glob(os.path.join(RAW_DIR, "L*_*_S*_V*.json")) + glob.glob(
        os.path.join(RAW_DIR, "[0-9]*_S*_V*.json")
    )
    return sorted(files, key=raw_file_sort_key)


def main():
    parser = argparse.ArgumentParser(description="Transforma datos nacionales para frontend.")
    parser.add_argument("--skip-ai", action="store_true", help="No llama a Gemini para nuevas categorizaciones.")
    parser.add_argument("--rebuild", action="store_true", help="Regenera todo ignorando overrides existentes.")
    parser.add_argument(
        "--allow-shrink",
        action="store_true",
        help="Permite publicar menos votaciones por legislatura que las ya publicadas.",
    )
    args = parser.parse_args()

    skip_ai = args.skip_ai
    api_key = os.environ.get("GEMINI_API_KEY")

    cache = load_cache()
    raw_files = list_raw_files()

    if not raw_files:
        print("No hay archivos JSON en data/raw/", file=sys.stderr)
        sys.exit(1)

    print(f"Procesando {len(raw_files)} archivos...")
    BATCH_SIZE = 20

    # First pass: load all files and collect uncached texts
    file_data_list = []
    uncached = {}  # hash -> texto, insertion-ordered

    for filepath in raw_files:
        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"  Saltando {os.path.basename(filepath)}: {e}", file=sys.stderr)
            continue

        info = data.get("informacion", {})
        texto = info.get("textoExpediente", "").strip()
        h = text_hash(texto)
        basename = os.path.basename(filepath)
        # Extract legislatura from filename (LXIII_...) or fallback
        file_leg = basename.split("_")[0][1:] if basename.startswith("L") else ""

        file_data_list.append(
            {
                "data": data,
                "hash": h,
                "titulo_original": info.get("titulo", "").strip(),
                "fecha": parse_congress_date(info.get("fecha", "")),
                "subgrupo_titulo": info.get("tituloSubGrupo", "").strip(),
                "sesion": info.get("sesion", ""),
                "numero_votacion": info.get("numeroVotacion", ""),
                "file_leg": file_leg,
            }
        )

        if h not in cache and not skip_ai and api_key:
            uncached.setdefault(h, texto)

    # Shrink guard before spending AI quota or touching any output.
    new_counts = {}
    for item in file_data_list:
        leg = item["file_leg"] or get_leg(item["fecha"])
        if leg:
            new_counts[leg] = new_counts.get(leg, 0) + 1
    shrinkage = find_shrinkage(published_counts_by_leg(), new_counts)
    if shrinkage and not args.allow_shrink:
        detail = ", ".join(f"{leg}: {prev} -> {new}" for leg, (prev, new) in sorted(shrinkage.items()))
        print(
            f"::error title=Transform nacional::data/raw está incompleto ({detail}). "
            "No se sobrescriben los datos publicados. Usa --allow-shrink si es intencionado.",
            file=sys.stderr,
        )
        sys.exit(2)

    # Batch categorize uncached texts with Gemini
    if uncached:
        with open(PROMPT_FILE, "r", encoding="utf-8") as f:
            prompt_text = f.read()

        pending = list(uncached.items())
        total_batches = (len(pending) + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"  {len(pending)} textos por categorizar en {total_batches} lotes...")

        for batch_idx in range(0, len(pending), BATCH_SIZE):
            batch = pending[batch_idx:batch_idx + BATCH_SIZE]
            batch_num = batch_idx // BATCH_SIZE + 1
            print(f"  Lote {batch_num}/{total_batches} ({len(batch)} textos)...")

            result_map = ai_utils.categorize_batch(batch, api_key, prompt_text)
            cache.update(result_map)
            if len(result_map) < len(batch):
                print(f"  WARN: lote {batch_num} sin categorizar {len(batch) - len(result_map)} textos", file=sys.stderr)

            # Save cache after each batch (resume-friendly)
            save_cache(cache)

    # Second pass: build votacion records using cache
    VALID_CAT_LIST = sorted(ai_utils.VALID_CATEGORIES)
    cat_to_idx = {c: i for i, c in enumerate(VALID_CAT_LIST)}
    preserved_meta_by_id, preserved_detail_by_id = ({}, {}) if args.rebuild else load_existing_overrides()
    if preserved_meta_by_id:
        print(f"Preserving curated meta fields for {len(preserved_meta_by_id)} existing votes.")

    vot_meta_list = []
    vot_results_list = []
    tag_counts = {}

    dep_fotos = {}
    if os.path.exists(FOTO_MAP_FILE):
        with open(FOTO_MAP_FILE, encoding="utf-8") as f:
            dep_fotos = json.load(f)

    dep_provs = {}
    if os.path.exists(PROVINCIA_MAP_FILE):
        with open(PROVINCIA_MAP_FILE, encoding="utf-8") as f:
            dep_provs = json.load(f)

    unique_diputados = {}
    unique_grupos = set()

    votos_by_leg = {}
    vot_detail_by_leg = {}
    seen_ids = set()

    for item in file_data_list:
        data = item["data"]
        fecha = item["fecha"]
        cat_data = cache.get(item["hash"], ai_utils._fallback_categorization())

        leg = item["file_leg"] or get_leg(fecha)
        if not leg:
            continue
        vote_id = f"{leg}-{item['sesion']}-{item['numero_votacion']}"
        if vote_id in seen_ids:
            print(f"  WARN: votación duplicada {vote_id}, se ignora", file=sys.stderr)
            continue
        seen_ids.add(vote_id)
        preserved_meta = preserved_meta_by_id.get(vote_id, {})
        preserved_detail = preserved_detail_by_id.get(vote_id, {})

        titulo_ciudadano = preserved_meta.get("titulo_ciudadano", cat_data.get("titulo_ciudadano", "Sin título"))
        categoria = preserved_meta.get("categoria_label", cat_data.get("categoria_principal", "Otros"))
        etiquetas = preserved_meta.get("etiquetas", cat_data.get("etiquetas", []) + ["nacional"])
        if not isinstance(etiquetas, list):
            etiquetas = cat_data.get("etiquetas", []) + ["nacional"]
        etiquetas = [t for t in etiquetas if isinstance(t, str) and t.strip()]
        if "nacional" not in etiquetas:
            etiquetas.append("nacional")
        resumen = preserved_detail.get("resumen", cat_data.get("resumen_sencillo", ""))
        proponente = preserved_meta.get("proponente", cat_data.get("proponente", ""))
        subgrupo = preserved_detail.get("subgrupo", classify_subgrupo(item["subgrupo_titulo"]))
        subgrupo_detalle = preserved_detail.get("subgrupo_detalle", item["subgrupo_titulo"])

        if leg not in votos_by_leg:
            votos_by_leg[leg] = []
            vot_detail_by_leg[leg] = {}

        vot_idx = len(vot_meta_list)
        counts, entries, asentimiento = tally_votes(data)
        by_group = {}

        for dip_id, raw_group, code in entries:
            if not dip_id:
                continue

            grupo = normalize_group_name(raw_group)
            if not grupo and dip_id in unique_diputados:
                grupo = unique_diputados[dip_id]["grupo"]
            if not grupo:
                grupo = "No Adscrito"

            unique_grupos.add(grupo)

            if dip_id not in unique_diputados:
                unique_diputados[dip_id] = {
                    "nombre": dip_id,
                    "grupo": grupo,
                    "foto": dep_fotos.get(dip_id),
                    "provincia": dep_provs.get(dip_id),
                }
            elif grupo != "No Adscrito":
                # Files are processed chronologically, so this keeps the most
                # recent concrete group (e.g. after a change of group).
                unique_diputados[dip_id]["grupo"] = grupo

            votos_by_leg[leg].append([vot_idx, dip_id, grupo, code])

            if grupo not in by_group:
                by_group[grupo] = {1: 0, 2: 0, 3: 0, 4: 0}
            by_group[grupo][code] += 1

        favor, contra, abstencion = counts["favor"], counts["contra"], counts["abstencion"]
        vot_meta_list.append({
            "id": vote_id,
            "legislatura": leg,
            "fecha": fecha,
            "titulo_ciudadano": titulo_ciudadano,
            "categoria": cat_to_idx.get(categoria, cat_to_idx["Otros"]),
            "etiquetas": etiquetas,
            "proponente": proponente,
        })

        vot_result = {
            "favor": favor,
            "contra": contra,
            "abstencion": abstencion,
            "total": favor + contra + abstencion,
            "result": vote_result(favor, contra, asentimiento),
            "margin": abs(favor - contra),
            "proponente": proponente,
        }
        if asentimiento:
            vot_result["asentimiento"] = True
        vot_results_list.append(vot_result)

        vot_detail_by_leg[leg][vot_idx] = {
            "resumen": resumen,
            "textoOficial": item["titulo_original"],
            "urlCongreso": congress_date_url(leg, fecha),
            "subgrupo": subgrupo,
            "subgrupo_detalle": subgrupo_detalle,
            "group_majority": group_majorities(by_group),
        }

        for t in etiquetas:
            tag_counts[t] = tag_counts.get(t, 0) + 1

    # Final indexing and file generation
    sorted_dips = sorted(unique_diputados.keys(), key=lambda x: unique_diputados[x]["nombre"])
    dip_id_to_idx = {d_id: i for i, d_id in enumerate(sorted_dips)}

    sorted_grupos = sorted(unique_grupos)
    grupo_to_idx = {g: i for i, g in enumerate(sorted_grupos)}

    # Per-deputy stats in a single pass over all votes.
    blank_stats = {"favor": 0, "contra": 0, "abstencion": 0, "no_vota": 0, "total": 0, "loyal": 0}
    stats_by_dip = {d_id: dict(blank_stats, legs=set()) for d_id in sorted_dips}
    code_field = {1: "favor", 2: "contra", 3: "abstencion", 4: "no_vota"}
    for leg, v_list in votos_by_leg.items():
        details = vot_detail_by_leg[leg]
        for vot_idx, dip_id, grupo, code in v_list:
            stats = stats_by_dip[dip_id]
            stats[code_field[code]] += 1
            if code in (1, 2, 3):
                stats["total"] += 1
                stats["legs"].add(leg)
                if details[vot_idx]["group_majority"].get(grupo) == code:
                    stats["loyal"] += 1

    dip_stats = []
    for d_id in sorted_dips:
        stats = stats_by_dip[d_id]
        dip_stats.append({
            "favor": stats["favor"],
            "contra": stats["contra"],
            "abstencion": stats["abstencion"],
            "no_vota": stats["no_vota"],
            "total": stats["total"],
            "mainGrupo": grupo_to_idx[unique_diputados[d_id]["grupo"]],
            "loyalty": round(stats["loyal"] / stats["total"], 4) if stats["total"] > 0 else 0,
            # Most recent first: the frontend loads legislaturas[0] eagerly.
            "legislaturas": sorted(stats["legs"], key=roman_to_int, reverse=True),
        })

    # Replace ids/names with indices
    for v_list in votos_by_leg.values():
        for entry in v_list:
            entry[1] = dip_id_to_idx[entry[1]]
            entry[2] = grupo_to_idx[entry[2]]

    # Group affinity
    group_affinity_by_leg = {}
    for leg_id in list(votos_by_leg.keys()) + [""]:
        ga = {}
        for vi, v_meta in enumerate(vot_meta_list):
            if leg_id and v_meta["legislatura"] != leg_id:
                continue
            gm = vot_detail_by_leg[v_meta["legislatura"]][vi]["group_majority"]
            g_keys = sorted(gm.keys())
            for a in range(len(g_keys)):
                for b in range(a + 1, len(g_keys)):
                    ga_idx, gb_idx = grupo_to_idx[g_keys[a]], grupo_to_idx[g_keys[b]]
                    key = f"{ga_idx},{gb_idx}" if ga_idx < gb_idx else f"{gb_idx},{ga_idx}"
                    if key not in ga:
                        ga[key] = {"same": 0, "total": 0}
                    ga[key]["total"] += 1
                    if gm[g_keys[a]] == gm[g_keys[b]]:
                        ga[key]["same"] += 1
        if ga:
            group_affinity_by_leg[leg_id] = ga

    sorted_by_date = sorted(range(len(vot_meta_list)), key=lambda i: (vot_meta_list[i]["fecha"], i), reverse=True)
    meta = {
        "diputados": [unique_diputados[d_id]["nombre"] for d_id in sorted_dips],
        "grupos": sorted_grupos,
        "categorias": VALID_CAT_LIST,
        "votaciones": vot_meta_list,
        "votResults": vot_results_list,
        "tagCounts": tag_counts,
        "topTags": sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:30],
        "sortedVotIdxByDate": sorted_by_date,
        "dipStats": dip_stats,
        "groupAffinityByLeg": group_affinity_by_leg,
        "votsByExp": {},  # Optional for now
        "votIdById": {v["id"]: i for i, v in enumerate(vot_meta_list)},
        "dipFotos": [unique_diputados[d_id]["foto"] for d_id in sorted_dips],
        "dipProvincias": [unique_diputados[d_id]["provincia"] for d_id in sorted_dips],
    }

    # Featured votes
    featured_ids = []
    if os.path.exists(FEATURED_FILE):
        with open(FEATURED_FILE, "r", encoding="utf-8") as f:
            featured_ids = json.load(f).get("nacional", [])

    def get_manifest_vote(idx):
        v_meta = vot_meta_list[idx]
        v_res = vot_results_list[idx]
        return {
            "id": v_meta["id"],
            "titulo_ciudadano": v_meta["titulo_ciudadano"],
            "fecha": v_meta["fecha"],
            "categoria": VALID_CAT_LIST[v_meta["categoria"]],
            "etiquetas": v_meta["etiquetas"],
            "subTipo": vot_detail_by_leg[v_meta["legislatura"]][idx].get("subgrupo", ""),
            "proponente": v_res.get("proponente", ""),
            "result": v_res["result"],
            "favor": v_res["favor"],
            "contra": v_res["contra"],
            "abstencion": v_res["abstencion"],
            "total": v_res["total"],
            "margin": v_res["margin"],
        }

    latest_indices = sorted_by_date[:10]
    tight_indices = sorted(
        [i for i in range(len(vot_meta_list)) if vot_results_list[i]["total"] > 300],
        key=lambda i: vot_results_list[i]["margin"],
    )[:10]

    vot_id_to_idx = meta["votIdById"]
    featured_indices = [vot_id_to_idx[fid] for fid in featured_ids if fid in vot_id_to_idx]
    missing_featured = [fid for fid in featured_ids if fid not in vot_id_to_idx]
    if missing_featured:
        print(f"  WARN: votaciones destacadas inexistentes: {missing_featured}", file=sys.stderr)

    manifest = {
        "updatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "stats": {
            "diputados": len(sorted_dips),
            "votaciones": len(vot_meta_list),
            "votos": sum(len(v) for v in votos_by_leg.values()),
        },
        "topTags": sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:20],
        "heroExamples": [
            ["subir_pensiones", "Quien voto subir pensiones?"],
            ["facilitar_acceso_vivienda", "Acceso a vivienda"],
            ["combatir_cambio_climatico", "Cambio climatico"],
            ["reformar_codigo_penal", "Reforma penal"],
            ["proteger_sanidad_publica", "Sanidad publica"],
        ],
        "latestVotes": [get_manifest_vote(i) for i in latest_indices],
        "tightVotes": [get_manifest_vote(i) for i in tight_indices],
        "featuredVotes": [get_manifest_vote(i) for i in featured_indices],
    }

    # Votes files first and meta last: meta is what the shrink guard and the
    # override loader read, so it must only change once everything else did.
    for leg, v_list in votos_by_leg.items():
        write_json(
            os.path.join(PUBLIC_DIR, f"votos_{leg}.json"),
            {"votos": v_list, "detail": vot_detail_by_leg[leg]},
        )
    write_json(MANIFEST_FILE, manifest)
    write_json(META_FILE, meta)
    sync_ambitos_legislaturas(votos_by_leg.keys())

    print(f"Transformación completada: {len(vot_meta_list)} votaciones.")
    for leg in sorted(new_counts, key=roman_to_int):
        print(f"  {leg}: {new_counts[leg]} votaciones")


if __name__ == "__main__":
    main()
