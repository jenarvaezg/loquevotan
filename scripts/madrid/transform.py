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
        raw_deps_list = json.load(f)
        raw_deps_map = {d["id"]: d for d in raw_deps_list}
    
    cache_file = f"{RAW_DIR}/cache_categorias.json"
    cache = {}
    if os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            cache = json.load(f)
            
    # 2. Collect unique deputies and groups across all legislatures
    deputados_all = {}
    grupos_all = set()
    
    # Track titles for AI categorization
    titles_to_categorize = []
    
    for v in all_raw_votes:
        for voto in v["votos"]:
            if voto["diputadoId"] not in deputados_all:
                deputados_all[voto["diputadoId"]] = {
                    "id": voto["diputadoId"],
                    "nombre": voto["diputado"],
                    "grupo": voto["grupo"],
                    "foto": raw_deps_map.get(voto["diputadoId"], {}).get("foto")
                }
            grupos_all.add(voto["grupo"])
            
        # Check if title is in cache
        if v["titulo"] not in cache and v["titulo"] != "Votación sin título":
            if not any(t[0] == v["titulo"] for t in titles_to_categorize):
                titles_to_categorize.append((v["titulo"], v["titulo"]))

    # 3. Categorize with AI if needed
    if titles_to_categorize and api_key:
        print(f"Categorizing {len(titles_to_categorize)} new titles for Madrid...")
        with open(PROMPT_FILE, "r") as f:
            prompt_text = f.read()
            
        BATCH_SIZE = 30
        for i in range(0, len(titles_to_categorize), BATCH_SIZE):
            batch = titles_to_categorize[i:i+BATCH_SIZE]
            print(f"  Lote {i//BATCH_SIZE + 1}/{(len(titles_to_categorize)-1)//BATCH_SIZE + 1}...")
            results = ai_utils.categorize_batch(batch, api_key, prompt_text)
            cache.update(results)
            
        # Save updated cache
        with open(cache_file, "w") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)

    diputados_list = sorted(list(deputados_all.values()), key=lambda x: x["nombre"])
    grupos_list = sorted(list(grupos_all))
    
    # Create maps for indexing
    dip_id_to_idx = {d["id"]: i for i, d in enumerate(diputados_list)}
    grupo_to_idx = {g: i for i, g in enumerate(grupos_list)}
    
    # 4. Categories and tags
    categorias_all = {"Otros"}
    for item in cache.values():
        categorias_all.add(item.get("categoria_principal", item.get("categoria", "Otros")))
    
    categorias_list = sorted(list(categorias_all))
    cat_to_idx = {c: i for i, c in enumerate(categorias_list)}
    
    # 5. Process each legislature
    votaciones_meta_list = []
    vot_results = []
    tag_counts = {}
    
    votos_by_leg = {leg: [] for leg in LEGISLATURAS}
    vot_detail_by_leg = {leg: {} for leg in LEGISLATURAS}
    
    # Sort all votes by date descending
    all_raw_votes.sort(key=lambda x: x["fecha"], reverse=True)
    
    for i, v in enumerate(all_raw_votes):
        cat_info = cache.get(v["titulo"], {
            "categoria_principal": "Otros",
            "etiquetas": [],
            "resumen_sencillo": "Votación en la Asamblea de Madrid",
            "titulo_ciudadano": v["titulo"]
        })
        
        vot_idx = i
        leg_roman = v["id"].split("-")[1] 
        leg_key = leg_roman 
        
        favor = 0
        contra = 0
        abstencion = 0
        no_vota = 0
        for voto in v["votos"]:
            s = voto["voto"]
            if s == "si": favor += 1
            elif s == "no": contra += 1
            elif s == "abstencion": abstencion += 1
            else: no_vota += 1
            
            votos_by_leg[leg_key].append([
                vot_idx,
                dip_id_to_idx[voto["diputadoId"]],
                grupo_to_idx[voto["grupo"]],
                1 if s == "si" else 2 if s == "no" else 3 if s == "abstencion" else 4
            ])
            
        votaciones_meta_list.append({
            "id": v["id"],
            "legislatura": leg_roman,
            "fecha": v["fecha"],
            "titulo_ciudadano": cat_info.get("titulo_ciudadano", v["titulo"]),
            "categoria": cat_to_idx[cat_info.get("categoria_principal", cat_info.get("categoria", "Otros"))],
            "etiquetas": cat_info.get("etiquetas", []) + ["madrid"]
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
        
        # Merge tags including institutions
        all_tags = cat_info.get("etiquetas", []) + ["madrid"]
        for tag in all_tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
            
        vot_detail_by_leg[leg_key][vot_idx] = {
            "resumen": cat_info.get("resumen_sencillo", "Votación en la Asamblea de Madrid"),
            "textoOficial": v["titulo"],
            "urlMadrid": "https://www.asambleamadrid.es/"
        }

    # 5. Generate meta file
    meta = {
        "diputados": [d["nombre"] for d in diputados_list],
        "grupos": grupos_list,
        "categorias": categorias_list,
        "votaciones": votaciones_meta_list,
        "votResults": vot_results,
        "tagCounts": tag_counts,
        "topTags": sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:20],
        "sortedVotIdxByDate": list(range(len(votaciones_meta_list))), 
        "dipStats": [[0,0,0,0] for _ in diputados_list],
        "groupAffinityByLeg": {leg: [] for leg in LEGISLATURAS}, 
        "votsByExp": {},
        "votIdById": {v["id"]: i for i, v in enumerate(votaciones_meta_list)},
        "dipFotos": [d.get("foto") for d in diputados_list]
    }
    
    # Calculate dipStats
    for leg in LEGISLATURAS:
        for v in votos_by_leg[leg]:
            dip_idx = v[1]
            sense = v[3]
            meta["dipStats"][dip_idx][sense-1] += 1

    with open(META_FILE, "w") as f:
        json.dump(meta, f, separators=(',', ':'))
        
    # 6. Generate votes files
    for leg in LEGISLATURAS:
        if not votos_by_leg[leg]: continue
        with open(f"{OUTPUT_DIR}/votos_{leg}.json", "w") as f:
            json.dump({
                "votos": votos_by_leg[leg],
                "detail": vot_detail_by_leg[leg]
            }, f, separators=(',', ':'))
            
    # 7. Update ambitos config
    if os.path.exists(AMBITOS_CONFIG):
        with open(AMBITOS_CONFIG, "r") as f:
            config = json.load(f)
        
        # Add or update Madrid entry
        found = False
        for a in config["ambitos"]:
            if a["id"] == "madrid":
                a["legislaturas"] = LEGISLATURAS
                found = True
                break
        
        if not found:
            config["ambitos"].append({
                "id": "madrid",
                "nombre": "Asamblea de Madrid",
                "legislaturas": LEGISLATURAS
            })
        
        with open(AMBITOS_CONFIG, "w") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
            
    print(f"Transformed {len(votaciones_meta_list)} total votaciones for {AMBITO}")

if __name__ == "__main__":
    transform()
