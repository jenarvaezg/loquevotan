import json
import os
import hashlib
import datetime

# Configuration
AMBITO = "andalucia"
RAW_FILE = f"data/{AMBITO}/votos_XII_raw.json"
CACHE_FILE = f"data/{AMBITO}/cache_categorias.json"
OUTPUT_DIR = f"public/data/{AMBITO}"
META_FILE = f"{OUTPUT_DIR}/votaciones_meta.json"
MANIFEST_FILE = f"public/data/manifest_home.json"

def transform():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    with open(RAW_FILE, "r") as f:
        raw_votes = json.load(f)
    
    with open(CACHE_FILE, "r") as f:
        cache = json.load(f)
        
    # 1. Collect unique deputies and groups
    # Load raw deputies to get photos
    try:
        with open(f"data/{AMBITO}/diputados_raw.json", "r") as f:
            raw_deps_list = json.load(f)
            raw_deps_map = {d["id"]: d for d in raw_deps_list}
    except:
        raw_deps_map = {}

    deputados_all = {}
    grupos_all = set()
    
    for v in raw_votes:
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
    
    # 2. Collect unique categories and tags
    categorias_all = {"Otros"}
    for item in cache.values():
        categorias_all.add(item["categoria"])
    
    categorias_list = sorted(list(categorias_all))
    cat_to_idx = {c: i for i, c in enumerate(categorias_list)}
    
    # 3. Process votaciones
    votaciones_list = []
    vot_results = []
    tag_counts = {}
    
    # Split votes by legislature (Andalusia only has XII for now)
    votos_by_leg = {"XII": []}
    vot_detail_by_leg = {"XII": {}}
    
    for i, v in enumerate(raw_votes):
        cat_info = cache.get(v["titulo"], {
            "categoria": "Otros",
            "etiquetas": ["andalucia"],
            "resumen": "Votación en el Parlamento de Andalucía",
            "titulo_ciudadano": v["titulo"]
        })
        
        vot_idx = i
        
        # Calculate totals
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
            
            # Store individual vote
            votos_by_leg["XII"].append([
                vot_idx,
                dip_id_to_idx[voto["diputadoId"]],
                grupo_to_idx[voto["grupo"]],
                1 if s == "si" else 2 if s == "no" else 3 if s == "abstencion" else 4
            ])
            
        votaciones_list.append({
            "id": v["id"],
            "leg": "XII",
            "fecha": v["fecha"],
            "tit": cat_info["titulo_ciudadano"],
            "cat": cat_to_idx[cat_info["categoria"]],
            "tags": cat_info["etiquetas"]
        })
        
        vot_results.append([favor, contra, abstencion, no_vota])
        
        for tag in cat_info["etiquetas"]:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
            
        vot_detail_by_leg["XII"][vot_idx] = {
            "resumen": cat_info["resumen"],
            "textoOficial": v["titulo"],
            "urlAndalucia": f"https://www.parlamentodeandalucia.es/webdinamica/portal-web-parlamento/pdf.do?tipodoc=diario&id={v.get('id', '')}"
        }

    # 4. Generate meta file
    # Try to find group logos or full names (simplified for now)
    # In Congreso we have a more complex mapping, for Andalusia we'll use abbreviations as names
    
    meta = {
        "diputados": [d["nombre"] for d in diputados_list],
        "grupos": grupos_list,
        "categorias": categorias_list,
        "votaciones": votaciones_list,
        "votResults": vot_results,
        "tagCounts": tag_counts,
        "topTags": sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:20],
        "sortedVotIdxByDate": list(range(len(votaciones_list))), 
        "dipStats": [[0,0,0,0] for _ in diputados_list],
        "groupAffinityByLeg": {"XII": []}, 
        "votsByExp": {},
        "votIdById": {v["id"]: i for i, v in enumerate(votaciones_list)},
        "dipFotos": [d.get("foto") for d in diputados_list]
    }
    
    # Calculate dipStats
    for v in votos_by_leg["XII"]:
        dip_idx = v[1]
        sense = v[3]
        meta["dipStats"][dip_idx][sense-1] += 1

    with open(META_FILE, "w") as f:
        json.dump(meta, f, separators=(',', ':'))
        
    # 5. Generate votes files
    for leg, v_list in votos_by_leg.items():
        with open(f"{OUTPUT_DIR}/votos_{leg}.json", "w") as f:
            json.dump({
                "votos": v_list,
                "detail": vot_detail_by_leg[leg]
            }, f, separators=(',', ':'))
            
    print(f"Transformed {len(votaciones_list)} votaciones for {AMBITO}")

if __name__ == "__main__":
    transform()
