import json
import os
import hashlib
import datetime
import sys

# Add root dir to path to import ai_utils
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import ai_utils

# Configuration
AMBITO = "madrid"
RAW_DIR = f"data/{AMBITO}"
OUTPUT_DIR = f"public/data/{AMBITO}"
META_FILE = f"{OUTPUT_DIR}/votaciones_meta.json"
AMBITOS_CONFIG = "public/data/ambitos.json"
PROMPT_FILE = "scripts/prompt_categorizacion.txt"

LEGISLATURAS = ["XIII"]

def transform():
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
        diputados_list = json.load(f)
        
    cache_file = f"{RAW_DIR}/cache_categorias.json"
    cache = {}
    if os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            cache = json.load(f)
            
    # 2. Track titles for AI categorization
    titles_to_categorize = []
    for v in all_raw_votes:
        if v["titulo"] not in cache and v["titulo"] != "Votación sin título":
            if not any(t[0] == v["titulo"] for t in titles_to_categorize):
                titles_to_categorize.append((v["titulo"], v["titulo"]))

    # 3. AI Categorization
    if titles_to_categorize and api_key:
        print(f"Categorizing {len(titles_to_categorize)} Madrid votes...")
        with open(PROMPT_FILE, "r") as f:
            prompt_text = f.read()
        results = ai_utils.categorize_batch(titles_to_categorize, api_key, prompt_text)
        cache.update(results)
        with open(cache_file, "w") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)

    # 4. Prepare indexing
    grupos_all = sorted(list(set(d["grupo"] for d in diputados_list)))
    grupo_to_idx = {g: i for i, g in enumerate(grupos_all)}
    dip_id_to_idx = {d["id"]: i for i, d in enumerate(diputados_list)}
    
    categorias_all = {"Otros"}
    for item in cache.values():
        categorias_all.add(item.get("categoria_principal", "Otros"))
    categorias_list = sorted(list(categorias_all))
    cat_to_idx = {c: i for i, c in enumerate(categorias_list)}
    
    # 5. Process votes and EXPAND to individual deputies
    vot_meta_list = []
    vot_results_list = []
    tag_counts = {}
    
    votos_by_leg = {leg: [] for leg in LEGISLATURAS}
    vot_detail_by_leg = {leg: {} for leg in LEGISLATURAS}
    
    # Sort by date
    all_raw_votes.sort(key=lambda x: x["fecha"], reverse=True)
    
    for i, v in enumerate(all_raw_votes):
        cat_info = cache.get(v["titulo"], {
            "titulo_ciudadano": v["titulo"],
            "categoria_principal": "Otros",
            "etiquetas": [],
            "resumen_sencillo": "Votación en la Asamblea de Madrid"
        })
        
        vot_idx = i
        leg = "XIII"
        
        # Expand group votes to individuals
        group_votes = v.get("group_votes", {})
        res_raw = v.get("results_raw", {})
        
        for d in diputados_list:
            sense_str = group_votes.get(d["grupo"], "no_vota")
            code = 4
            if sense_str == "si": code = 1
            elif sense_str == "no": code = 2
            elif sense_str == "abstencion": code = 3
            
            votos_by_leg[leg].append([
                vot_idx,
                dip_id_to_idx[d["id"]],
                grupo_to_idx[d["grupo"]],
                code
            ])
            
        vot_meta_list.append({
            "id": v["id"],
            "legislatura": leg,
            "fecha": v["fecha"],
            "titulo_ciudadano": cat_info.get("titulo_ciudadano", v["titulo"]),
            "categoria": cat_to_idx.get(cat_info.get("categoria_principal"), cat_to_idx["Otros"]),
            "etiquetas": cat_info.get("etiquetas", []) + ["madrid"]
        })
        
        vot_results_list.append({
            "favor": res_raw.get("favor", 0),
            "contra": res_raw.get("contra", 0),
            "abstencion": res_raw.get("abstencion", 0),
            "total": res_raw.get("present", 135),
            "result": "Aprobada" if res_raw.get("favor", 0) > res_raw.get("contra", 0) else "Rechazada",
            "margin": abs(res_raw.get("favor", 0) - res_raw.get("contra", 0)),
            "proponente": cat_info.get("proponente", "Desconocido")
        })
        
        vot_detail_by_leg[leg][vot_idx] = {
            "resumen": cat_info.get("resumen_sencillo", "Votación en la Asamblea de Madrid"),
            "textoOficial": v["titulo"],
            "urlMadrid": "https://www.asambleamadrid.es/actividad-parlamentaria/sesiones",
            "metadatos": v.get("metadatos", {})
        }
        
        for t in cat_info.get("etiquetas", []) + ["madrid"]:
            tag_counts[t] = tag_counts.get(t, 0) + 1

    # 6. Generate meta file
    # Calculate dipStats
    dip_stats = []
    for d in diputados_list:
        fav, con, abs_v, tot = 0, 0, 0, 0
        for leg in LEGISLATURAS:
            for v_entry in votos_by_leg[leg]:
                if v_entry[1] == dip_id_to_idx[d["id"]]:
                    code = v_entry[3]
                    if code == 1: fav += 1
                    elif code == 2: con += 1
                    elif code == 3: abs_v += 1
                    if code < 4: tot += 1
        
        dip_stats.append({
            "favor": fav,
            "contra": con,
            "abstencion": abs_v,
            "total": tot,
            "mainGrupo": grupo_to_idx[d["grupo"]],
            "loyalty": 1.0, # Assumed 100% since it's group-deduced
            "legislaturas": ["XIII"]
        })

    meta = {
        "diputados": [d["nombre"] for d in diputados_list],
        "grupos": grupos_all,
        "categorias": categorias_list,
        "votaciones": vot_meta_list,
        "votResults": vot_results_list,
        "tagCounts": tag_counts,
        "topTags": sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:30],
        "sortedVotIdxByDate": list(range(len(vot_meta_list))),
        "dipStats": dip_stats,
        "groupAffinityByLeg": {"XIII": {}}, # Will be populated by regular use if needed
        "votsByExp": {},
        "votIdById": {v["id"]: i for i, v in enumerate(vot_meta_list)},
        "dipFotos": [d.get("foto") for d in diputados_list]
    }
    
    with open(META_FILE, "w") as f:
        json.dump(meta, f, separators=(',', ':'))
        
    for leg in LEGISLATURAS:
        if not votos_by_leg[leg]: continue
        with open(f"{OUTPUT_DIR}/votos_{leg}.json", "w") as f:
            json.dump({
                "votos": votos_by_leg[leg],
                "detail": vot_detail_by_leg[leg]
            }, f, separators=(',', ':'))
            
    print(f"Transformed {len(vot_meta_list)} Madrid votes.")

if __name__ == "__main__":
    transform()
