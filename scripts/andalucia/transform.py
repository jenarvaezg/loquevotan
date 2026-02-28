import json
import os
import hashlib
import datetime

# Configuration
AMBITO = "andalucia"
RAW_DIR = f"data/{AMBITO}"
OUTPUT_DIR = f"public/data/{AMBITO}"
META_FILE = f"{OUTPUT_DIR}/votaciones_meta.json"
MANIFEST_FILE = f"public/data/manifest_home.json"

LEGISLATURAS = ["XII", "XI", "X", "IX"]

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
    
    cache_file = f"{RAW_DIR}/cache_categorias.json"
    cache = {}
    if os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            cache = json.load(f)
            
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
    categorias_all = {"Otros"}
    for item in cache.values():
        categorias_all.add(item["categoria"])
    
    categorias_list = sorted(list(categorias_all))
    cat_to_idx = {c: i for i, c in enumerate(categorias_list)}
    
    # 4. Process each legislature
    votaciones_meta_list = []
    vot_results = []
    tag_counts = {}
    
    votos_by_leg = {leg: [] for leg in LEGISLATURAS}
    vot_detail_by_leg = {leg: {} for leg in LEGISLATURAS}
    
    # Sort all votes by date descending
    all_raw_votes.sort(key=lambda x: x["fecha"], reverse=True)
    
    for i, v in enumerate(all_raw_votes):
        cat_info = cache.get(v["titulo"], {
            "categoria": "Otros",
            "etiquetas": ["andalucia"],
            "resumen": "Votación en el Parlamento de Andalucía",
            "titulo_ciudadano": v["titulo"]
        })
        
        vot_idx = i
        leg_roman = v["id"].split("-")[1] # e.g. AND-XII-77-1 -> XII
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
            "tit": cat_info["titulo_ciudadano"],
            "cat": cat_to_idx[cat_info["categoria"]],
            "tags": cat_info["etiquetas"]
        })
        
        vot_results.append([favor, contra, abstencion, no_vota])
        
        for tag in cat_info["etiquetas"]:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
            
        vot_detail_by_leg[leg_key][vot_idx] = {
            "resumen": cat_info["resumen"],
            "textoOficial": v["titulo"],
            "urlAndalucia": f"https://www.parlamentodeandalucia.es/webdinamica/portal-web-parlamento/pdf.do?tipodoc=diario&id={v.get('id', '')}"
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
    
    # Calculate dipStats across all legislaturas
    for leg in LEGISLATURAS:
        for v in votos_by_leg[leg]:
            dip_idx = v[1]
            sense = v[3]
            meta["dipStats"][dip_idx][sense-1] += 1

    with open(META_FILE, "w") as f:
        json.dump(meta, f, separators=(',', ':'))
        
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
    transform()
