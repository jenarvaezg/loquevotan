import json
import os
import hashlib
import datetime
import sys
import re
import argparse

# Add root dir to path to import ai_utils
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import ai_utils

# Configuration
AMBITO = "andalucia"
RAW_DIR = f"data/{AMBITO}"
OUTPUT_DIR = f"public/data/{AMBITO}"
META_FILE = f"{OUTPUT_DIR}/votaciones_meta.json"
MANIFEST_FILE = f"{OUTPUT_DIR}/manifest_home.json"
AMBITOS_CONFIG = "public/data/ambitos.json"
PROMPT_FILE = "scripts/prompt_categorizacion.txt"

LEGISLATURAS = ["XII", "XI", "X", "IX"]
SCOPE_TAG = "andalucia"

FALLBACK_TITLE = "Asunto parlamentario sin clasificar"
MAX_CITIZEN_TITLE_WORDS = 18
EXPEDIENTE_PATTERN = re.compile(r"\b\d{1,2}-\d+/[A-Z]+-\d+\b", re.IGNORECASE)

PROCEDURAL_REWRITES = [
    # Parliamentary boilerplate that adds noise without user value.
    (r"^proposición no de ley en pleno(?:\s+\d{1,2}-\d+/[a-z]+-\d+)?\s*,?\s*relativa a\s+", ""),
    (r"^proposición no de ley en pleno\s+", ""),
    (r"^moción\s+relativa\s+a\s+", ""),
    (r"^debate de la comunicación del consejo de gobierno sobre\s+", "Debate sobre "),
    (
        r"^propuesta de toma en consideración(?: por el pleno)? de la proposición de ley(?: a tramitar ante la mesa del congreso de los diputados)?(?: relativa a)?\s+",
        "",
    ),
    (r"^propuesta de toma en consideración(?: por el pleno)?\s+", ""),
    (r"^convalidación o derogación del decreto ley(?: por el que)?\s+", ""),
]


def prettify_official_title(title):
    """Build a readable citizen title from the official expediente text."""
    if not title:
        return FALLBACK_TITLE

    clean = " ".join(title.split())
    clean = re.sub(r"^\d{1,2}-\d+/[A-Z]+-\d+\s*,\s*", "", clean)
    clean = clean.strip(" .,:;")
    if not clean:
        return FALLBACK_TITLE

    lowered = clean.lower()
    pretty = lowered[:1].upper() + lowered[1:]
    pretty = re.sub(r"\bandalucía\b", "Andalucía", pretty, flags=re.IGNORECASE)
    return pretty


def normalize_citizen_title(citizen_title, official_title):
    """Clean noisy titles into concise user-facing wording."""
    title = (citizen_title or "").strip()
    if not title or title == FALLBACK_TITLE:
        title = prettify_official_title(official_title)

    title = " ".join(title.split())
    title = title.replace("ycontrol", "y control")
    title = EXPEDIENTE_PATTERN.sub("", title)
    title = re.sub(r",\s*proposición no de ley en pleno.*$", "", title, flags=re.IGNORECASE)

    for pattern, replacement in PROCEDURAL_REWRITES:
        title = re.sub(pattern, replacement, title, flags=re.IGNORECASE)

    title = re.sub(r"\s*,\s*,", ", ", title)
    title = re.sub(r"\s{2,}", " ", title)
    title = title.strip(" ,.;:-")

    if not title:
        title = prettify_official_title(official_title)

    title = re.sub(r"\bandalucía\b", "Andalucía", title, flags=re.IGNORECASE)
    title = title[0].upper() + title[1:]

    words = title.split()
    if len(words) > MAX_CITIZEN_TITLE_WORDS:
        title = " ".join(words[:MAX_CITIZEN_TITLE_WORDS]).rstrip(",.;:") + "..."

    return title


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
        if isinstance(vote.get("titulo_ciudadano"), str) and vote["titulo_ciudadano"].strip():
            override["titulo_ciudadano"] = vote["titulo_ciudadano"].strip()
        if isinstance(vote.get("etiquetas"), list) and vote["etiquetas"]:
            override["etiquetas"] = vote["etiquetas"]
        if isinstance(vote.get("subTipo"), str) and vote["subTipo"].strip():
            override["subTipo"] = vote["subTipo"].strip()
        if isinstance(vote.get("proponente"), str) and vote["proponente"].strip():
            override["proponente"] = vote["proponente"].strip()
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
    all_raw_votes = []
    for leg in LEGISLATURAS:
        raw_file = f"{RAW_DIR}/votos_{leg}_raw.json"
        if os.path.exists(raw_file):
            with open(raw_file, "r") as f:
                votes = json.load(f)
                all_raw_votes.extend(votes)
    
    with open(f"{RAW_DIR}/diputados_raw.json", "r") as f:
        raw_deps_list = json.load(f)
        raw_deps_map = {d["id"]: d for d in raw_deps_list}
    
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
    
    # Track titles for AI categorization
    titles_to_categorize = []
    
    for v in all_raw_votes:
        for voto in v["votos"]:
            if voto["diputadoId"] not in deputados_all:
                dep_data = raw_deps_map.get(voto["diputadoId"], {})
                deputados_all[voto["diputadoId"]] = {
                    "id": voto["diputadoId"],
                    "nombre": voto["diputado"],
                    "grupo": voto["grupo"],
                    "foto": dep_data.get("foto"),
                    "provincia": dep_data.get("provincia")
                }
            grupos_all.add(voto["grupo"])
        
        # Categorize new titles, and retry entries that are still placeholders.
        cache_entry = cache.get(v["titulo"])
        needs_categorization = (
            cache_entry is None
            or cache_entry.get("titulo_ciudadano") == FALLBACK_TITLE
        )
        if needs_categorization and v["titulo"] != "Votación sin título":
            # Avoid duplicates in batch
            if not any(t[0] == v["titulo"] for t in titles_to_categorize):
                titles_to_categorize.append((v["titulo"], v["titulo"]))

    # 3. Categorize with AI if needed
    if titles_to_categorize and api_key:
        print(f"Categorizing {len(titles_to_categorize)} new titles for Andalusia...")
        with open(PROMPT_FILE, "r") as f:
            prompt_text = f.read()
            
        # Limit to 30 at a time to stay under tokens/limits
        BATCH_SIZE = 30
        for i in range(0, len(titles_to_categorize), BATCH_SIZE):
            batch = titles_to_categorize[i:i+BATCH_SIZE]
            print(f"  Lote {i//BATCH_SIZE + 1}/{(len(titles_to_categorize)-1)//BATCH_SIZE + 1}...")
            results = ai_utils.categorize_batch(batch, api_key, prompt_text)
            cache.update(results)
            
        # Save updated cache
        with open(cache_file, "w") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
    elif titles_to_categorize and not api_key:
        print("GEMINI_API_KEY no disponible: se mantiene caché existente sin forzar fallbacks.")

    diputados_list = sorted(list(deputados_all.values()), key=lambda x: x["nombre"])
    grupos_list = sorted(list(grupos_all))
    
    # Create maps for indexing
    dip_id_to_idx = {d["id"]: i for i, d in enumerate(diputados_list)}
    grupo_to_idx = {g: i for i, g in enumerate(grupos_list)}
    
    # 3. Categories and tags
    categorias_all = {"Otros"}
    for item in cache.values():
        categorias_all.add(item.get("categoria_principal", item.get("categoria", "Otros")))
    
    categorias_list = sorted(list(categorias_all))
    cat_to_idx = {c: i for i, c in enumerate(categorias_list)}
    
    # 4. Process each legislature
    votaciones_meta_list = []
    vot_results = []
    tag_counts = {}
    group_majority = {}
    
    votos_by_leg = {leg: [] for leg in LEGISLATURAS}
    vot_detail_by_leg = {leg: {} for leg in LEGISLATURAS}
    vots_by_exp = {} # exp_id -> list of vot_idx
    
    # Sort all votes by date descending
    all_raw_votes.sort(key=lambda x: x["fecha"], reverse=True)
    
    for i, v in enumerate(all_raw_votes):
        cat_info = cache.get(v["titulo"], {
            "categoria_principal": "Otros",
            "etiquetas": [SCOPE_TAG],
            "resumen_sencillo": "Votación en el Parlamento de Andalucía",
            "titulo_ciudadano": prettify_official_title(v["titulo"]),
        })
        if cat_info.get("titulo_ciudadano") == FALLBACK_TITLE:
            # Keep a readable fallback title instead of showing the generic placeholder.
            cat_info = dict(cat_info)
            cat_info["titulo_ciudadano"] = prettify_official_title(v["titulo"])

        preserved_meta = preserved_meta_by_id.get(v["id"], {})
        categoria_label = preserved_meta.get(
            "categoria_label",
            cat_info.get("categoria_principal", cat_info.get("categoria", "Otros")),
        )
        if categoria_label not in cat_to_idx:
            categoria_label = cat_info.get("categoria_principal", cat_info.get("categoria", "Otros"))

        etiquetas = preserved_meta.get("etiquetas", cat_info.get("etiquetas", []))
        if not isinstance(etiquetas, list):
            etiquetas = cat_info.get("etiquetas", [])
        etiquetas = [t for t in etiquetas if isinstance(t, str) and t.strip()]
        if SCOPE_TAG not in etiquetas:
            etiquetas.append(SCOPE_TAG)
        
        vot_idx = i
        leg_roman = v["id"].split("-")[1] # e.g. AND-XII-77-1 -> XII
        leg_key = leg_roman 

        # Extract expediente from title (e.g. 12-22/PNLP-000003)
        exp_match = re.search(r"(\d+-\d+/[A-Z]+-\d+)", v["titulo"])
        exp_id = exp_match.group(1) if exp_match else None
        if exp_id:
            if exp_id not in vots_by_exp:
                vots_by_exp[exp_id] = []
            vots_by_exp[exp_id].append(vot_idx)
        
        favor = 0
        contra = 0
        abstencion = 0
        no_vota = 0
        
        by_group = {}
        
        for voto in v["votos"]:
            s = voto["voto"]
            code = 4
            if s == "si": 
                favor += 1
                code = 1
            elif s == "no": 
                contra += 1
                code = 2
            elif s == "abstencion": 
                abstencion += 1
                code = 3
            else: 
                no_vota += 1
                code = 4
            
            grp_idx = grupo_to_idx[voto["grupo"]]
            
            if grp_idx not in by_group:
                by_group[grp_idx] = {1: 0, 2: 0, 3: 0, 4: 0}
            by_group[grp_idx][code] += 1
            
            votos_by_leg[leg_key].append([
                vot_idx,
                dip_id_to_idx[voto["diputadoId"]],
                grp_idx,
                code
            ])
            
        titulo_ciudadano = normalize_citizen_title(
            preserved_meta.get("titulo_ciudadano", cat_info.get("titulo_ciudadano", v["titulo"])),
            v["titulo"],
        )
        sub_tipo = preserved_meta.get("subTipo", cat_info.get("subTipo", ""))
        proponente = preserved_meta.get("proponente", cat_info.get("proponente", ""))
        resumen = preserved_detail_by_id.get(v["id"], {}).get(
            "resumen",
            cat_info.get("resumen_sencillo", cat_info.get("resumen", "")),
        )

        votaciones_meta_list.append({
            "id": v["id"],
            "legislatura": leg_roman,
            "fecha": v["fecha"],
            "titulo_ciudadano": titulo_ciudadano,
            "categoria": cat_to_idx.get(categoria_label, cat_to_idx["Otros"]),
            "etiquetas": etiquetas,
            "exp": exp_id,
            "subTipo": sub_tipo,
            "proponente": proponente
        })
        
        total = favor + contra + abstencion
        result = "Aprobada" if favor > contra else ("Rechazada" if contra > favor else "Empate")
        vot_results.append({
            "favor": favor,
            "contra": contra,
            "abstencion": abstencion,
            "total": total,
            "result": result,
            "margin": abs(favor - contra),
        })
        
        gm = {}
        for g_idx, c in by_group.items():
            if c[1] >= c[2] and c[1] >= c[3]:
                gm[g_idx] = 1
            elif c[2] >= c[3]:
                gm[g_idx] = 2
            else:
                gm[g_idx] = 3
        group_majority[vot_idx] = gm
        
        for tag in etiquetas:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
            
        vot_detail_by_leg[leg_key][vot_idx] = {
            "resumen": resumen,
            "textoOficial": v["titulo"],
            "urlCongreso": f"https://www.parlamentodeandalucia.es/webdinamica/portal-web-parlamento/pdf.do?tipodoc=diario&id={v.get('id', '')}"
        }

    # 5. Generate meta file
    dip_stats = []
    vbd = {} # dipIdx -> list of (votIdx, code, grpIdx, leg_roman)
    
    for leg in LEGISLATURAS:
        for v in votos_by_leg[leg]:
            votIdx, dipIdx, grpIdx, code = v
            if dipIdx not in vbd:
                vbd[dipIdx] = []
            vbd[dipIdx].append((votIdx, code, grpIdx, leg))
            
    for di in range(len(diputados_list)):
        indices = vbd.get(di, [])
        t = {1: 0, 2: 0, 3: 0, 4: 0}
        grupo_count = {}
        loyal = 0
        leg_set = set()
        
        for (votIdx, code, grpIdx, leg) in indices:
            t[code] += 1
            grupo_count[grpIdx] = grupo_count.get(grpIdx, 0) + 1
            maj = group_majority.get(votIdx, {})
            if maj.get(grpIdx) == code:
                loyal += 1
            leg_set.add(leg)
            
        total = t[1] + t[2] + t[3] # Exclude no_vota from total if we align with National
        main_grupo = -1
        if grupo_count:
            main_grupo = max(grupo_count, key=grupo_count.get)
            
        dip_stats.append({
            "favor": t[1],
            "contra": t[2],
            "abstencion": t[3],
            "no_vota": t[4],
            "total": total,
            "mainGrupo": main_grupo,
            "loyalty": round(loyal / total, 4) if total > 0 else 0,
            "legislaturas": list(leg_set)
        })
        
    # Pre-computando afinidad entre grupos
    group_affinity_by_leg = {}
    for leg_id in LEGISLATURAS + [""]:
        ga = {}
        for vi in range(len(votaciones_meta_list)):
            if leg_id and votaciones_meta_list[vi].get("legislatura") != leg_id:
                continue
            gm = group_majority.get(vi, {})
            g_keys = sorted(gm.keys())
            for a in range(len(g_keys)):
                for b in range(a + 1, len(g_keys)):
                    ka, kb = g_keys[a], g_keys[b]
                    key = f"{ka},{kb}" if ka < kb else f"{kb},{ka}"
                    if key not in ga:
                        ga[key] = {"same": 0, "total": 0}
                    ga[key]["total"] += 1
                    if gm[ka] == gm[kb]:
                        ga[key]["same"] += 1
        if ga:
            group_affinity_by_leg[leg_id] = ga

    meta = {
        "diputados": [d["nombre"] for d in diputados_list],
        "grupos": grupos_list,
        "categorias": categorias_list,
        "votaciones": votaciones_meta_list,
        "votResults": vot_results,
        "tagCounts": tag_counts,
        "topTags": sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:20],
        "sortedVotIdxByDate": list(range(len(votaciones_meta_list))), 
        "dipStats": dip_stats,
        "groupAffinityByLeg": group_affinity_by_leg, 
        "votsByExp": vots_by_exp,
        "votIdById": {v["id"]: i for i, v in enumerate(votaciones_meta_list)},
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
            featured_ids = json.load(f).get("andalucia", [])

    def get_manifest_vote(idx):
        v_meta = votaciones_meta_list[idx]
        v_res = vot_results[idx]
        return {
            "id": v_meta["id"],
            "titulo_ciudadano": v_meta["titulo_ciudadano"],
            "fecha": v_meta["fecha"],
            "categoria": categorias_list[v_meta["categoria"]],
            "etiquetas": v_meta["etiquetas"],
            "subTipo": v_meta["subTipo"], 
            "proponente": v_meta["proponente"],
            "result": v_res["result"],
            "favor": v_res["favor"],
            "contra": v_res["contra"],
            "abstencion": v_res["abstencion"],
            "total": v_res["total"],
            "margin": v_res["margin"]
        }

    latest_indices = sorted(range(len(votaciones_meta_list)), key=lambda i: (votaciones_meta_list[i]["fecha"], i), reverse=True)[:10]
    tight_indices = sorted([i for i in range(len(votaciones_meta_list)) if vot_results[i]["total"] > 100], 
                          key=lambda i: vot_results[i]["margin"])[:10]
    
    featured_indices = []
    for fid in featured_ids:
        for i, v in enumerate(votaciones_meta_list):
            if v["id"] == fid:
                featured_indices.append(i)
                break

    manifest = {
        "updatedAt": datetime.datetime.now().isoformat(),
        "stats": {
            "diputados": len(diputados_list),
            "votaciones": len(votaciones_meta_list),
            "votos": sum(len(v) for v in votos_by_leg.values())
        },
        "topTags": sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:20],
        "heroExamples": [
            ["sanidad", "Sanidad pública"],
            ["vivienda", "Acceso a vivienda"],
            ["educacion", "Educación"],
            ["medio_ambiente", "Doñana y medio ambiente"],
            ["andalucia", "Todo Andalucía"]
        ],
        "latestVotes": [get_manifest_vote(i) for i in latest_indices],
        "tightVotes": [get_manifest_vote(i) for i in tight_indices],
        "featuredVotes": [get_manifest_vote(i) for i in featured_indices]
    }

    with open(MANIFEST_FILE, "w") as f:
        json.dump(manifest, f, separators=(',', ':'))

    # 6. Generate votes files
    for leg in LEGISLATURAS:
        if not votos_by_leg[leg] and leg != "XII": continue
        with open(f"{OUTPUT_DIR}/votos_{leg}.json", "w") as f:
            json.dump({
                "votos": votos_by_leg[leg],
                "detail": vot_detail_by_leg[leg]
            }, f, separators=(',', ':'))
            
    # 7. Update ambitos config
    config_file = "public/data/ambitos.json"
    if os.path.exists(config_file):
        with open(config_file, "r") as f:
            config = json.load(f)
        
        # Find andalucia entry
        for a in config["ambitos"]:
            if a["id"] == "andalucia":
                a["legislaturas"] = LEGISLATURAS
                break
        
        with open(config_file, "w") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
            
    print(f"Transformed {len(votaciones_meta_list)} total votaciones for {AMBITO}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transforma datos de Andalucía para frontend.")
    parser.add_argument("--rebuild", action="store_true", help="Regenera todo ignorando overrides existentes.")
    args = parser.parse_args()
    transform(rebuild=args.rebuild)
