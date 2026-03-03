import json
import os
import datetime
import sys
import argparse
import re

# Add root dir to path to import ai_utils
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import ai_utils

# Configuration
AMBITO = "madrid"
RAW_DIR = f"data/{AMBITO}"
OUTPUT_DIR = f"public/data/{AMBITO}"
META_FILE = f"{OUTPUT_DIR}/votaciones_meta.json"
MANIFEST_FILE = f"{OUTPUT_DIR}/manifest_home.json"
AMBITOS_CONFIG = "public/data/ambitos.json"
PROMPT_FILE = "scripts/prompt_categorizacion.txt"

LEGISLATURAS = ["XIII", "XII", "XI", "X"]
SCOPE_TAG = "madrid"
ROMAN_TO_NUM = {"X": "10", "XI": "11", "XII": "12", "XIII": "13"}
NUM_TO_ROMAN = {value: key for key, value in ROMAN_TO_NUM.items()}
VOTE_CODE_BY_SENSE = {"si": 1, "sí": 1, "no": 2, "abstencion": 3, "abstención": 3, "no_vota": 4}
UNKNOWN_GROUP_TOKENS = {"", "unknown", "desconocido", "null", "none", "n/a", "na"}
GENERIC_AI_TITLE_PATTERNS = [
    r"^votaci[oó]n(?:\s+de\s+tr[aá]mite(?:\s+.+)?|\s+ordinaria|\s+parlamentaria)$",
    r"^votaci[oó]n\s+sobre\s+un\s+asunto(?:\s+parlamentario)?(?:\s+.+)?$",
    r"^votaci[oó]n\s+sobre\s+un\s+asunto\s+interno(?:\s+de\s+la\s+comisi[oó]n)?$",
    r"^votaci[oó]n\s+de\s+un\s+conjunto\s+de\s+enmiendas(?:\s+sin\s+detalle)?$",
]


def normalize_group_name(group_name):
    value = str(group_name or "").strip()
    if value.lower() in UNKNOWN_GROUP_TOKENS:
        return "No Adscrito"
    return value


def is_placeholder_title(value):
    title = str(value or "").strip().lower()
    return title in {"", "votación", "votacion", "votación sin título", "votacion sin titulo", "votación desconocida", "votacion desconocida"}


def is_generic_ai_title(value):
    title = str(value or "").strip().lower()
    if not title:
        return True
    for pattern in GENERIC_AI_TITLE_PATTERNS:
        if re.match(pattern, title, re.I):
            return True
    return False


def normalize_public_title(raw_title):
    title = str(raw_title or "").strip()
    if is_placeholder_title(title):
        return ""
    if re.match(r"^\(?pausa\.?\)?\s*el$", title, re.I):
        return ""
    if re.match(r"^votaci[oó]n\s+de\s+la$", title, re.I):
        return ""
    match = re.match(r"^votaci[oó]n\s+relacionada\s+con:\s*(.+)$", title, re.I)
    if match:
        title = match.group(1).strip()
    normalized = re.sub(r"\s+", " ", title).strip(" .;:,")
    if len(normalized) < 14:
        return ""
    return normalized


def resolve_citizen_title(raw_title, ai_title):
    clean_ai = str(ai_title or "").strip()
    if clean_ai and not is_placeholder_title(clean_ai) and not is_generic_ai_title(clean_ai):
        return clean_ai
    fallback = normalize_public_title(raw_title)
    return fallback or "Asunto parlamentario sin clasificar"


def normalize_vote_sense(vote_value):
    value = str(vote_value or "").strip().lower()
    if value in {"si", "sí"}:
        return "si"
    if value == "no":
        return "no"
    if value in {"abstencion", "abstención"}:
        return "abstencion"
    return "no_vota"


def to_int(value):
    try:
        return int(value)
    except Exception:
        return 0

def load_existing_overrides():
    if not os.path.exists(META_FILE):
        return {}, {}

    try:
        with open(META_FILE, "r") as f:
            previous_meta = json.load(f)
    except Exception:
        return {}, {}

    previous_categories = previous_meta.get("categorias", [])
    previous_votes = previous_meta.get("votaciones", [])

    previous_detail_by_leg = {}
    for leg in LEGISLATURAS:
        votes_path = f"{OUTPUT_DIR}/votos_{leg}.json"
        if not os.path.exists(votes_path):
            continue
        try:
            with open(votes_path, "r") as f:
                previous_detail_by_leg[leg] = json.load(f).get("detail", {})
        except Exception:
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
        if isinstance(vote.get("titulo_ciudadano"), str):
            previous_title = vote["titulo_ciudadano"].strip()
            if previous_title and not is_placeholder_title(previous_title) and not is_generic_ai_title(previous_title):
                override["titulo_ciudadano"] = previous_title
        if isinstance(vote.get("etiquetas"), list) and vote["etiquetas"]:
            override["etiquetas"] = vote["etiquetas"]
        if override:
            meta_overrides[vote_id] = override

        leg = vote.get("legislatura")
        detail = previous_detail_by_leg.get(leg, {}).get(str(idx))
        if isinstance(detail, dict):
            resumen = detail.get("resumen")
            if isinstance(resumen, str) and resumen.strip():
                detail_overrides[vote_id] = {"resumen": resumen.strip()}

    return meta_overrides, detail_overrides


def transform(rebuild=False):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    api_key = os.environ.get("GEMINI_API_KEY")
    
    # 1. Load all raw votes and deputies
    all_raw_votes_map = {}
    for leg in LEGISLATURAS:
        raw_file = f"{RAW_DIR}/votos_{leg}_raw.json"
        if os.path.exists(raw_file):
            with open(raw_file, "r") as f:
                votes = json.load(f)
                for v in votes:
                    all_raw_votes_map[v["id"]] = v
    
    all_raw_votes = list(all_raw_votes_map.values())
    
    with open(f"{RAW_DIR}/diputados_raw.json", "r") as f:
        raw_deps_list = json.load(f)
    
    cache_file = f"{RAW_DIR}/cache_categorias.json"
    cache = {}
    if os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            cache = json.load(f)

    preserved_meta_by_id, preserved_detail_by_id = ({}, {}) if rebuild else load_existing_overrides()
    if preserved_meta_by_id:
        print(f"Preserving curated meta fields for {len(preserved_meta_by_id)} existing votes.")
            
    # 2. Collect unique deputies and groups across all legislatures
    deputados_all = {}
    grupos_all = set()
    deputy_group_counts_by_leg = {}

    for dep in raw_deps_list:
        dep_id = dep.get("id")
        if not dep_id:
            continue
        group_name = normalize_group_name(dep.get("grupo"))
        deputies_leg = str(dep.get("nlegis", "")).strip()
        if deputies_leg:
            if deputies_leg not in deputy_group_counts_by_leg:
                deputy_group_counts_by_leg[deputies_leg] = {}
            deputy_group_counts_by_leg[deputies_leg][group_name] = deputy_group_counts_by_leg[deputies_leg].get(group_name, 0) + 1

        deputados_all[dep_id] = {
            "id": dep_id,
            "nombre": dep.get("nombre", ""),
            "grupo": group_name,
            "foto": dep.get("foto"),
            "provincia": dep.get("provincia", "Madrid"),
        }
        grupos_all.add(group_name)

    # Track titles for AI categorization
    titles_to_categorize = []
    seen_titles = set()
    for v in all_raw_votes:
        title = str(v.get("titulo", "")).strip()
        if is_placeholder_title(title):
            continue
        if title not in cache and title not in seen_titles:
            titles_to_categorize.append((title, title))
            seen_titles.add(title)
        for group_name in (v.get("group_votes") or {}).keys():
            grupos_all.add(normalize_group_name(group_name))

    # 3. Categorize with AI if needed
    if titles_to_categorize:
        if not api_key:
            print("GEMINI_API_KEY not found. Skipping AI categorization for Madrid.")
        else:
            print(f"Categorizing {len(titles_to_categorize)} new titles for Madrid...")
            with open(PROMPT_FILE, "r") as f:
                prompt_text = f.read()

            BATCH_SIZE = 20
            for i in range(0, len(titles_to_categorize), BATCH_SIZE):
                batch = titles_to_categorize[i:i + BATCH_SIZE]
                print(f"  Batch {i//BATCH_SIZE + 1}/{(len(titles_to_categorize)-1)//BATCH_SIZE + 1}...")
                results = ai_utils.categorize_batch(batch, api_key, prompt_text)
                cache.update(results)

                # Save updated cache after each batch
                with open(cache_file, "w") as f:
                    json.dump(cache, f, indent=2, ensure_ascii=False)

    diputados_list = sorted(list(deputados_all.values()), key=lambda x: x["nombre"])
    sorted_grupos = sorted(list(grupos_all))
    
    # Create maps for indexing
    dip_id_to_idx = {d["id"]: i for i, d in enumerate(diputados_list)}
    grupo_to_idx = {g: i for i, g in enumerate(sorted_grupos)}
    
    # 4. Categories and tags
    categorias_all = {"Otros"}
    for item in cache.values():
        categorias_all.add(item.get("categoria_principal", item.get("categoria", "Otros")))
    for override in preserved_meta_by_id.values():
        category_label = override.get("categoria_label")
        if isinstance(category_label, str) and category_label.strip():
            categorias_all.add(category_label.strip())
    
    categorias_list = sorted(list(categorias_all))
    cat_to_idx = {c: i for i, c in enumerate(categorias_list)}
    
    # 5. Process each legislature
    vot_meta_list = []
    vot_results_list = []
    tag_counts = {}
    group_majority = {}
    
    votos_by_leg = {leg: [] for leg in LEGISLATURAS}
    vot_detail_by_leg = {leg: {} for leg in LEGISLATURAS}
    
    # Sort all votes by date descending
    all_raw_votes.sort(key=lambda x: x["fecha"], reverse=True)
    
    for i, v in enumerate(all_raw_votes):
        leg_roman = v["id"].split("-")[1]
        leg_num = ROMAN_TO_NUM.get(leg_roman, leg_roman)
        leg_key = leg_roman
        vot_idx = i
        raw_title = str(v.get("titulo", "")).strip()

        cat_info = cache.get(raw_title, {
            "categoria_principal": "Otros",
            "etiquetas": [],
            "resumen_sencillo": "Votación en la Asamblea de Madrid",
            "titulo_ciudadano": raw_title
        })

        preserved_meta = preserved_meta_by_id.get(v["id"], {})
        categoria_label = preserved_meta.get(
            "categoria_label",
            cat_info.get("categoria_principal", cat_info.get("categoria", "Otros")),
        )
        if categoria_label not in cat_to_idx:
            categoria_label = cat_info.get("categoria_principal", cat_info.get("categoria", "Otros"))

        etiquetas = preserved_meta.get("etiquetas", cat_info.get("etiquetas", []) + [SCOPE_TAG])
        if not isinstance(etiquetas, list):
            etiquetas = cat_info.get("etiquetas", []) + [SCOPE_TAG]
        etiquetas = [t for t in etiquetas if isinstance(t, str) and t.strip()]
        if SCOPE_TAG not in etiquetas:
            etiquetas.append(SCOPE_TAG)
        titulo_ciudadano = preserved_meta.get(
            "titulo_ciudadano",
            resolve_citizen_title(raw_title, cat_info.get("titulo_ciudadano", raw_title)),
        )
        resumen = preserved_detail_by_id.get(v["id"], {}).get(
            "resumen",
            cat_info.get("resumen_sencillo", "Votación en la Asamblea de Madrid"),
        )

        favor, contra, abstencion, no_vota = 0, 0, 0, 0
        by_group = {}

        if v.get("votos"):
            for voto in v["votos"]:
                sense = normalize_vote_sense(voto.get("voto"))
                code = VOTE_CODE_BY_SENSE.get(sense, 4)
                if code == 1:
                    favor += 1
                elif code == 2:
                    contra += 1
                elif code == 3:
                    abstencion += 1
                else:
                    no_vota += 1

                grp_name = normalize_group_name(voto.get("grupo"))
                if grp_name not in by_group:
                    by_group[grp_name] = {1: 0, 2: 0, 3: 0, 4: 0}
                by_group[grp_name][code] += 1

                dip_id = voto.get("diputadoId")
                if dip_id in dip_id_to_idx and grp_name in grupo_to_idx:
                    votos_by_leg[leg_key].append([
                        vot_idx,
                        dip_id_to_idx[dip_id],
                        grupo_to_idx[grp_name],
                        code
                    ])
        else:
            # Madrid no publica voto nominal de forma consistente: mantenemos sólo mayoría por grupo.
            for raw_group, raw_sense in (v.get("group_votes") or {}).items():
                grp_name = normalize_group_name(raw_group)
                sense = normalize_vote_sense(raw_sense)
                code = VOTE_CODE_BY_SENSE.get(sense, 4)
                if grp_name not in by_group:
                    by_group[grp_name] = {1: 0, 2: 0, 3: 0, 4: 0}
                weight = deputy_group_counts_by_leg.get(leg_num, {}).get(grp_name, 1)
                by_group[grp_name][code] += weight
            
        vot_meta_list.append({
            "id": v["id"],
            "legislatura": leg_roman,
            "fecha": v["fecha"],
            "titulo_ciudadano": titulo_ciudadano,
            "categoria": cat_to_idx.get(categoria_label, cat_to_idx["Otros"]),
            "etiquetas": etiquetas
        })
        
        totals = v.get("totales") or {}
        if totals:
            favor = to_int(totals.get("favor"))
            contra = to_int(totals.get("contra"))
            abstencion = to_int(totals.get("abstencion"))
            total = to_int(totals.get("total"))
            if total <= 0:
                total = favor + contra + abstencion
            no_vota = max(0, total - (favor + contra + abstencion))
        else:
            total = favor + contra + abstencion

        result = "Aprobada" if favor > contra else ("Rechazada" if contra > favor else "Empate")
        vot_results_list.append({
            "favor": favor,
            "contra": contra,
            "abstencion": abstencion,
            "total": total,
            "result": result,
            "margin": abs(favor - contra),
        })
        
        # Calculate group majorities
        gm = {}
        for g_name, c in by_group.items():
            ranked_codes = sorted(c.items(), key=lambda item: (item[1], -item[0]), reverse=True)
            top_code, top_value = ranked_codes[0]
            gm[g_name] = top_code if top_value > 0 else 4
        group_majority[vot_idx] = gm
        
        for tag in etiquetas:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
            
        vot_detail_by_leg[leg_key][vot_idx] = {
            "resumen": resumen,
            "textoOficial": raw_title,
            "urlMadrid": "https://www.asambleamadrid.es/",
            "group_majority": gm
        }

    # 6. Calculate deputy stats
    dip_stats = []
    vbd = {} # dipIdx -> list of (votIdx, code, grpIdx, leg)
    for leg in LEGISLATURAS:
        for v_entry in votos_by_leg[leg]:
            votIdx, dipIdx, grpIdx, code = v_entry
            if dipIdx not in vbd: vbd[dipIdx] = []
            vbd[dipIdx].append((votIdx, code, grpIdx, leg))
            
    for di in range(len(diputados_list)):
        indices = vbd.get(di, [])
        t = {1: 0, 2: 0, 3: 0, 4: 0}
        grp_counts = {}
        loyal = 0
        leg_set = set()
        
        for (vIdx, code, gIdx, leg) in indices:
            t[code] += 1
            grp_counts[gIdx] = grp_counts.get(gIdx, 0) + 1
            maj = group_majority.get(vIdx, {})
            if maj.get(sorted_grupos[gIdx]) == code:
                loyal += 1
            leg_set.add(leg)
            
        total = t[1] + t[2] + t[3]
        main_g = max(grp_counts, key=grp_counts.get) if grp_counts else -1
        
        dep_id = diputados_list[di]["id"]
        dep_leg_num = dep_id.split("-")[1] if "-" in dep_id else ""
        dep_leg = NUM_TO_ROMAN.get(dep_leg_num, "XIII")

        dip_stats.append({
            "favor": t[1],
            "contra": t[2],
            "abstencion": t[3],
            "no_vota": t[4],
            "total": total,
            "mainGrupo": main_g,
            "loyalty": round(loyal / total, 4) if total > 0 else 0,
            "legislaturas": sorted(list(leg_set)) if leg_set else [dep_leg]
        })

    # 7. Group affinity
    group_affinity_by_leg = {}
    for leg_id in LEGISLATURAS + [""]:
        ga = {}
        for vi in range(len(vot_meta_list)):
            if leg_id and vot_meta_list[vi]["legislatura"] != leg_id: continue
            gm = group_majority.get(vi, {})
            g_names = sorted(gm.keys())
            for a in range(len(g_names)):
                for b in range(a + 1, len(g_names)):
                    na, nb = g_names[a], g_names[b]
                    ia, ib = grupo_to_idx[na], grupo_to_idx[nb]
                    key = f"{ia},{ib}" if ia < ib else f"{ib},{ia}"
                    if key not in ga: ga[key] = {"same": 0, "total": 0}
                    ga[key]["total"] += 1
                    if gm[na] == gm[nb]: ga[key]["same"] += 1
        if ga: group_affinity_by_leg[leg_id] = ga

    # 8. Generate final meta
    meta = {
        "diputados": [d["nombre"] for d in diputados_list],
        "grupos": sorted_grupos,
        "categorias": categorias_list,
        "votaciones": vot_meta_list,
        "votResults": vot_results_list,
        "tagCounts": tag_counts,
        "topTags": sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:30],
        "sortedVotIdxByDate": list(range(len(vot_meta_list))), 
        "dipStats": dip_stats,
        "groupAffinityByLeg": group_affinity_by_leg, 
        "votsByExp": {},
        "votIdById": {v["id"]: i for i, v in enumerate(vot_meta_list)},
        "dipFotos": [d.get("foto") for d in diputados_list],
        "dipProvincias": [d.get("provincia") for d in diputados_list]
    }
    
    with open(META_FILE, "w") as f:
        json.dump(meta, f, separators=(',', ':'))
        
    # Generate manifest_home.json
    FEATURED_FILE = "data/featured_votes.json"
    featured_ids = []
    if os.path.exists(FEATURED_FILE):
        with open(FEATURED_FILE, "r") as f:
            featured_ids = json.load(f).get("madrid", [])

    def get_manifest_vote(idx):
        v_meta = vot_meta_list[idx]
        v_res = vot_results_list[idx]
        return {
            "id": v_meta["id"],
            "titulo_ciudadano": v_meta["titulo_ciudadano"],
            "fecha": v_meta["fecha"],
            "categoria": categorias_list[v_meta["categoria"]],
            "etiquetas": v_meta["etiquetas"],
            "result": v_res["result"],
            "favor": v_res["favor"],
            "contra": v_res["contra"],
            "abstencion": v_res["abstencion"],
            "total": v_res["total"],
            "margin": v_res["margin"],
        }

    canonical_idx_by_id = meta["votIdById"]

    def canonicalize_indices(indices):
        unique = []
        seen_ids = set()
        for idx in indices:
            vote_id = vot_meta_list[idx]["id"]
            canonical_idx = canonical_idx_by_id.get(vote_id)
            if canonical_idx is None or vote_id in seen_ids:
                continue
            unique.append(canonical_idx)
            seen_ids.add(vote_id)
        return unique

    latest_candidates = sorted(
        range(len(vot_meta_list)),
        key=lambda idx: (vot_meta_list[idx]["fecha"], idx),
        reverse=True,
    )
    tight_candidates = sorted(
        [idx for idx in range(len(vot_meta_list)) if vot_results_list[idx]["total"] > 30],
        key=lambda idx: vot_results_list[idx]["margin"],
    )
    latest_indices = canonicalize_indices(latest_candidates)[:10]
    tight_indices = canonicalize_indices(tight_candidates)[:10]

    featured_indices = []
    for vote_id in featured_ids:
        idx = canonical_idx_by_id.get(vote_id)
        if idx is not None:
            featured_indices.append(idx)

    manifest = {
        "updatedAt": datetime.datetime.now().isoformat(),
        "stats": {
            "diputados": len(diputados_list),
            "votaciones": len(vot_meta_list),
            "votos": sum(v["total"] for v in vot_results_list),
        },
        "topTags": sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:20],
        "heroExamples": [
            ["sanidad", "Sanidad Madrid"],
            ["educacion", "Becas comedor"],
            ["vivienda", "Ley de Vivienda"],
            ["madrid", "Todo Madrid"],
        ],
        "latestVotes": [get_manifest_vote(idx) for idx in latest_indices],
        "tightVotes": [get_manifest_vote(idx) for idx in tight_indices],
        "featuredVotes": [get_manifest_vote(idx) for idx in featured_indices],
    }
    with open(MANIFEST_FILE, "w") as f:
        json.dump(manifest, f, separators=(',', ':'))

    # 9. Generate votes files
    for leg in LEGISLATURAS:
        with open(f"{OUTPUT_DIR}/votos_{leg}.json", "w") as f:
            json.dump({
                "votos": votos_by_leg[leg],
                "detail": vot_detail_by_leg[leg]
            }, f, separators=(',', ':'))
            
    # 10. Update ambitos config
    if os.path.exists(AMBITOS_CONFIG):
        with open(AMBITOS_CONFIG, "r") as f:
            config = json.load(f)
        for a in config["ambitos"]:
            if a["id"] == "madrid":
                a["legislaturas"] = LEGISLATURAS
                break
        with open(AMBITOS_CONFIG, "w") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
            
    print(f"Transformed {len(vot_meta_list)} Madrid votes.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transforma datos de Madrid para frontend.")
    parser.add_argument("--rebuild", action="store_true", help="Regenera todo ignorando overrides existentes.")
    args = parser.parse_args()
    transform(rebuild=args.rebuild)
