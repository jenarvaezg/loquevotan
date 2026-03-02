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
MANIFEST_FILE = f"{OUTPUT_DIR}/manifest_home.json"
AMBITOS_CONFIG = "public/data/ambitos.json"
PROMPT_FILE = "scripts/prompt_categorizacion.txt"

LEGISLATURAS = ["XIII", "XII", "XI", "X"]

def transform():
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
        # Map by id
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
    
    # Pre-process votes to get unique deputies and groups
    ROMAN_TO_NUM = {"X": "10", "XI": "11", "XII": "12", "XIII": "13"}
    for v in all_raw_votes:
        votos_list = v.get("votos")
        leg_roman = v["id"].split("-")[1]
        leg_num = ROMAN_TO_NUM.get(leg_roman, leg_roman)
        
        if not votos_list and "group_votes" in v:
            votos_list = []
            gv = v["group_votes"]
            for d_id, d_info in raw_deps_map.items():
                if d_info.get("nlegis") != leg_num: continue
                
                d_group = d_info.get("grupo", "")
                voto_sense = "no_vota"
                for g_key, sense in gv.items():
                    if g_key.lower() in d_group.lower() or d_group.lower() in g_key.lower():
                        voto_sense = sense
                        break
                votos_list.append({"diputadoId": d_id, "diputado": d_info["nombre"], "grupo": d_group, "voto": voto_sense})
        
        if not votos_list: continue
        
        for voto in votos_list:
            d_id = voto["diputadoId"]
            if d_id not in deputados_all:
                dep_data = raw_deps_map.get(d_id, {})
                deputados_all[d_id] = {
                    "id": d_id,
                    "nombre": voto["diputado"],
                    "grupo": voto["grupo"],
                    "foto": dep_data.get("foto"),
                    "provincia": "Madrid"
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
            print(f"  Batch {i//BATCH_SIZE + 1}/{(len(titles_to_categorize)-1)//BATCH_SIZE + 1}...")
            results = ai_utils.categorize_batch(batch, api_key, prompt_text)
            cache.update(results)
            
        # Save updated cache
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
        votos_list = v.get("votos")
        leg_roman = v["id"].split("-")[1] 
        leg_num = ROMAN_TO_NUM.get(leg_roman, leg_roman)
        
        if not votos_list and "group_votes" in v:
            votos_list = []
            gv = v["group_votes"]
            for d_id, d_info in raw_deps_map.items():
                if d_info.get("nlegis") != leg_num: continue
                d_group = d_info.get("grupo", "")
                voto_sense = "no_vota"
                for g_key, sense in gv.items():
                    if g_key.lower() in d_group.lower() or d_group.lower() in g_key.lower():
                        voto_sense = sense
                        break
                votos_list.append({"diputadoId": d_id, "voto": voto_sense, "grupo": d_group})

        if not votos_list: continue

        cat_info = cache.get(v["titulo"], {
            "categoria_principal": "Otros",
            "etiquetas": [],
            "resumen_sencillo": "Votación en la Asamblea de Madrid",
            "titulo_ciudadano": v["titulo"]
        })
        
        vot_idx = i
        leg_key = leg_roman 
        
        favor, contra, abstencion, no_vota = 0, 0, 0, 0
        by_group = {}
        for voto in votos_list:
            s = voto["voto"]
            code = 4
            if s == "si": favor += 1; code = 1
            elif s == "no": contra += 1; code = 2
            elif s == "abstencion": abstencion += 1; code = 3
            else: no_vota += 1; code = 4
            
            grp_name = voto["grupo"]
            if grp_name not in by_group:
                by_group[grp_name] = {1: 0, 2: 0, 3: 0, 4: 0}
            by_group[grp_name][code] += 1
            
            if voto["diputadoId"] in dip_id_to_idx:
                votos_by_leg[leg_key].append([
                    vot_idx,
                    dip_id_to_idx[voto["diputadoId"]],
                    grupo_to_idx[grp_name],
                    code
                ])
            
        vot_meta_list.append({
            "id": v["id"],
            "legislatura": leg_roman,
            "fecha": v["fecha"],
            "titulo_ciudadano": cat_info.get("titulo_ciudadano", v["titulo"]),
            "categoria": cat_to_idx.get(cat_info.get("categoria_principal", cat_info.get("categoria", "Otros")), cat_to_idx["Otros"]),
            "etiquetas": cat_info.get("etiquetas", []) + ["madrid"]
        })
        
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
            if c[1] >= c[2] and c[1] >= c[3]: gm[g_name] = 1
            elif c[2] >= c[3]: gm[g_name] = 2
            else: gm[g_name] = 3
        group_majority[vot_idx] = gm
        
        all_tags = cat_info.get("etiquetas", []) + ["madrid"]
        for tag in all_tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
            
        vot_detail_by_leg[leg_key][vot_idx] = {
            "resumen": cat_info.get("resumen_sencillo", "Votación en la Asamblea de Madrid"),
            "textoOficial": v["titulo"],
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
        
        dip_stats.append({
            "favor": t[1],
            "contra": t[2],
            "abstencion": t[3],
            "no_vota": t[4],
            "total": total,
            "mainGrupo": main_g,
            "loyalty": round(loyal / total, 4) if total > 0 else 0,
            "legislaturas": sorted(list(leg_set)) if leg_set else ["XIII"]
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
    manifest = {
        "stats": {
            "diputados": len(diputados_list),
            "votaciones": len(vot_meta_list),
            "votos": sum(len(v) for v in votos_by_leg.values())
        },
        "topTags": sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:20],
        "heroExamples": [
            ["sanidad", "Sanidad Madrid"],
            ["educacion", "Becas comedor"],
            ["vivienda", "Ley de Vivienda"],
            ["madrid", "Todo Madrid"]
        ],
        "latestVotes": [],
        "tightVotes": [],
        "featuredVotes": []
    }
    with open(MANIFEST_FILE, "w") as f:
        json.dump(manifest, f, separators=(',', ':'))

    # 9. Generate votes files
    for leg in LEGISLATURAS:
        if not votos_by_leg[leg]: 
            with open(f"{OUTPUT_DIR}/votos_{leg}.json", "w") as f:
                json.dump({"votos": [], "detail": {}}, f)
            continue
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
    transform()
