import json
import os
import hashlib
import datetime

# Configuration
AMBITO = "cyl"
RAW_DIR = f"data/{AMBITO}"
OUTPUT_DIR = f"public/data/{AMBITO}"
META_FILE = f"{OUTPUT_DIR}/votaciones_meta.json"
AMBITOS_CONFIG = "public/data/ambitos.json"

LEGISLATURAS = ["XI", "X"]

def transform():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
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
    
    # Use a dummy cache for now
    cache = {}
            
    # 2. Collect unique deputies and groups across all legislatures
    deputados_all = {}
    grupos_all = set()
    
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
            
    diputados_list = sorted(list(deputados_all.values()), key=lambda x: x["nombre"])
    grupos_list = sorted(list(grupos_all))
    
    # Create maps for indexing
    dip_id_to_idx = {d["id"]: i for i, d in enumerate(diputados_list)}
    grupo_to_idx = {g: i for i, g in enumerate(grupos_list)}
    
    # 3. Categories and tags
    categorias_list = ["Otros"]
    cat_to_idx = {"Otros": 0}
    
    # 4. Process each legislature
    votaciones_meta_list = []
    vot_results = []
    tag_counts = {"cyl": 0}
    
    votos_by_leg = {leg: [] for leg in LEGISLATURAS}
    vot_detail_by_leg = {leg: {} for leg in LEGISLATURAS}
    
    # Sort all votes by date descending
    all_raw_votes.sort(key=lambda x: x["fecha"], reverse=True)
    
    leg_map = {"11": "XI", "10": "X"}
    
    for i, v in enumerate(all_raw_votes):
        vot_idx = i
        leg_id = v["id"].split("-")[1] # 11 or 10
        leg_roman = leg_map.get(leg_id, "XI")
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
            "leg": leg_roman,
            "fecha": v["fecha"],
            "tit": v["titulo"],
            "cat": 0,
            "tags": ["cyl"]
        })
        
        vot_results.append([favor, contra, abstencion, no_vota])
        tag_counts["cyl"] += 1
            
        vot_detail_by_leg[leg_key][vot_idx] = {
            "resumen": "Votación nominal en las Cortes de Castilla y León",
            "textoOficial": v["titulo"],
            "urlCyL": f"https://www.ccyl.es/Publicaciones/TextoEntradaDiario?Legislatura={leg_id}&SeriePublicacion=DS(P)&NumeroPublicacion={v['id'].split('-')[2]}"
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
        
        # Add or update CyL entry
        found = False
        for a in config["ambitos"]:
            if a["id"] == "cyl":
                a["legislaturas"] = LEGISLATURAS
                found = True
                break
        
        if not found:
            config["ambitos"].append({
                "id": "cyl",
                "nombre": "Cortes de Castilla y León",
                "legislaturas": LEGISLATURAS
            })
        
        with open(AMBITOS_CONFIG, "w") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
            
    print(f"Transformed {len(votaciones_meta_list)} total nominal votaciones for {AMBITO}")

if __name__ == "__main__":
    transform()
