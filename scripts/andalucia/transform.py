import json
import os
import hashlib
import datetime
import sys

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
                dep_data = raw_deps_map.get(voto["diputadoId"], {})
                deputados_all[voto["diputadoId"]] = {
                    "id": voto["diputadoId"],
                    "nombre": voto["diputado"],
                    "grupo": voto["grupo"],
                    "foto": dep_data.get("foto"),
                    "provincia": dep_data.get("provincia")
                }
            grupos_all.add(voto["grupo"])
        
        # Check if title is in cache
        if v["titulo"] not in cache and v["titulo"] != "Votación sin título":
            # Avoid duplicates in batch
            if not any(t[0] == v["titulo"] for t in titles_to_categorize):
                titles_to_categorize.append((v["titulo"], v["titulo"]))

    # 3. Categorize with AI if needed
    if titles_to_categorize:
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
    
    # Sort all votes by date descending
    all_raw_votes.sort(key=lambda x: x["fecha"], reverse=True)
    
    for i, v in enumerate(all_raw_votes):
        cat_info = cache.get(v["titulo"], {
            "categoria_principal": "Otros",
            "etiquetas": ["andalucia"],
            "resumen_sencillo": "Votación en el Parlamento de Andalucía",
            "titulo_ciudadano": v["titulo"]
        })
        
        vot_idx = i
        leg_roman = v["id"].split("-")[1] # e.g. AND-XII-77-1 -> XII
        leg_key = leg_roman 
        
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
            
        votaciones_meta_list.append({
            "id": v["id"],
            "legislatura": leg_roman,
            "fecha": v["fecha"],
            "titulo_ciudadano": cat_info.get("titulo_ciudadano", v["titulo"]),
            "categoria": cat_to_idx[cat_info.get("categoria_principal", cat_info.get("categoria", "Otros"))],
            "etiquetas": cat_info.get("etiquetas", [])
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
        
        for tag in cat_info.get("etiquetas", []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
            
        vot_detail_by_leg[leg_key][vot_idx] = {
            "resumen": cat_info.get("resumen_sencillo", cat_info.get("resumen", "")),
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
        "votsByExp": {},
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
            "subTipo": "", 
            "proponente": "",
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
    transform()