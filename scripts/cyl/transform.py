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
AMBITO = "cyl"
RAW_DIR = f"data/{AMBITO}"
OUTPUT_DIR = f"public/data/{AMBITO}"
META_FILE = f"{OUTPUT_DIR}/votaciones_meta.json"
MANIFEST_FILE = f"{OUTPUT_DIR}/manifest_home.json"
AMBITOS_CONFIG = "public/data/ambitos.json"
PROMPT_FILE = "scripts/prompt_categorizacion.txt"

LEGISLATURAS = ["XI", "X", "IX", "VIII", "VII"]
SCOPE_TAG = "cyl"

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
        leg_id_raw = v["id"].split("-")[1] 
        for voto in v["votos"]:
            d_id = voto["diputadoId"]
            if voto["diputadoId"] not in deputados_all:
                # Try to find with possible prefixes
                dep_data = raw_deps_map.get(d_id)
                if not dep_data:
                    dep_data = raw_deps_map.get(f"CYL-{leg_id_raw}-{d_id}")
                if not dep_data:
                    dep_data = {}
                
                deputados_all[d_id] = {
                    "id": d_id,
                    "nombre": voto["diputado"],
                    "grupo": voto["grupo"],
                    "foto": dep_data.get("foto"),
                    "provincia": dep_data.get("provincia")
                }
            grupos_all.add(voto["grupo"])
            
        # Check if title is in cache
        if v["titulo"] not in cache and v["titulo"] != "Votación nominal":
            if not any(t[0] == v["titulo"] for t in titles_to_categorize):
                titles_to_categorize.append((v["titulo"], v["titulo"]))

    # 3. Categorize with AI if needed
    if titles_to_categorize:
        print(f"Categorizing {len(titles_to_categorize)} new titles for CyL...")
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
    
    votos_by_leg = {leg: [] for leg in LEGISLATURAS}
    vot_detail_by_leg = {leg: {} for leg in LEGISLATURAS}
    group_majority = {}
    vots_by_exp = {} # exp_id -> list of vot_idx
    
    # Sort all votes by date descending
    all_raw_votes.sort(key=lambda x: x["fecha"], reverse=True)
    
    leg_map_id = {"11": "XI", "10": "X", "9": "IX", "8": "VIII", "7": "VII"}
    
    for i, v in enumerate(all_raw_votes):
        cat_info = cache.get(v["titulo"], {
            "categoria_principal": "Otros",
            "etiquetas": [],
            "resumen_sencillo": "Votación nominal en las Cortes de Castilla y León",
            "titulo_ciudadano": v["titulo"]
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
        
        vot_idx = i
        leg_id_raw = v["id"].split("-")[1] 
        leg_roman = leg_map_id.get(leg_id_raw, "XI")
        leg_key = leg_roman 

        # Extract expediente from title (e.g. PNL/000123 or just 123)
        exp_id = None
        exp_match = re.search(r"([A-Z]+/\d+)", v["titulo"])
        if exp_match:
            exp_id = exp_match.group(1)
        else:
            # Fallback to look for just the number if it's clear
            exp_match = re.search(r"(?:No de Ley|nº|número)\s+(\d+)", v["titulo"])
            if exp_match:
                exp_id = exp_match.group(1)
        
        if exp_id:
            if exp_id not in vots_by_exp:
                vots_by_exp[exp_id] = []
            vots_by_exp[exp_id].append(vot_idx)
        
        favor, contra, abstencion, no_vota = 0, 0, 0, 0
        by_group = {}
        
        if v.get("votos"):
            for voto in v["votos"]:
                s = voto["voto"].lower()
                code = 4
                if s == "si" or s == "sí": 
                    favor += 1; code = 1
                elif s == "no": 
                    contra += 1; code = 2
                elif s == "abstencion" or s == "abstención": 
                    abstencion += 1; code = 3
                else: 
                    no_vota += 1; code = 4
                
                grp_name = voto["grupo"]
                if grp_name not in by_group:
                    by_group[grp_name] = {1: 0, 2: 0, 3: 0, 4: 0}
                by_group[grp_name][code] += 1
                
                votos_by_leg[leg_key].append([
                    vot_idx,
                    dip_id_to_idx[voto["diputadoId"]],
                    grupo_to_idx[grp_name],
                    code
                ])
        elif v.get("totales"):
            # Use totals for ordinary votes where individual votes are missing
            t = v["totales"]
            favor = t.get("favor", 0)
            contra = t.get("contra", 0)
            abstencion = t.get("abstencion", 0)
            total_emit = t.get("total", 0)
            no_vota = max(0, total_emit - (favor + contra + abstencion))
            
        sub_tipo = preserved_meta.get("subTipo", cat_info.get("subTipo", ""))
        proponente = preserved_meta.get("proponente", cat_info.get("proponente", v.get("proponente", "")))
        resumen = preserved_detail_by_id.get(v["id"], {}).get(
            "resumen",
            cat_info.get("resumen_sencillo", "Votación nominal en las Cortes de Castilla y León"),
        )
        titulo_ciudadano = preserved_meta.get("titulo_ciudadano", cat_info.get("titulo_ciudadano", v["titulo"]))

        vot_meta_list.append({
            "id": v["id"],
            "legislatura": leg_roman,
            "fecha": v["fecha"],
            "titulo_ciudadano": titulo_ciudadano,
            "categoria": cat_to_idx.get(categoria_label, cat_to_idx["Otros"]),
            "etiquetas": etiquetas,
            "proponente": proponente,
            "exp": exp_id,
            "subTipo": sub_tipo
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
        
        for tag in etiquetas:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
            
        vot_detail_by_leg[leg_key][vot_idx] = {
            "resumen": resumen,
            "textoOficial": v["titulo"],
            "urlCyL": f"https://www.ccyl.es/Publicaciones/TextoEntradaDiario?Legislatura={leg_id_raw}&SeriePublicacion=DS(P)&NumeroPublicacion={v['id'].split('-')[2]}",
            "group_majority": gm
        }

    # 6. Calculate deputy stats
    dip_stats = []
    vbd = {} # dipIdx -> list of (votIdx, code, grpIdx, leg)
    for leg in LEGISLATURAS:
        for v in votos_by_leg[leg]:
            votIdx, dipIdx, grpIdx, code = v
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
            if maj.get(grupos_list[gIdx]) == code:
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
            "legislaturas": sorted(list(leg_set))
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
        "grupos": grupos_list,
        "categorias": categorias_list,
        "votaciones": vot_meta_list,
        "votResults": vot_results_list,
        "tagCounts": tag_counts,
        "topTags": sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:30],
        "sortedVotIdxByDate": list(range(len(vot_meta_list))), 
        "dipStats": dip_stats,
        "groupAffinityByLeg": group_affinity_by_leg, 
        "votsByExp": vots_by_exp,
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
            featured_ids = json.load(f).get("cyl", [])

    def get_manifest_vote(idx):
        v_meta = vot_meta_list[idx]
        v_res = vot_results_list[idx]
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
        key=lambda i: (vot_meta_list[i]["fecha"], i),
        reverse=True
    )
    tight_candidates = sorted(
        [i for i in range(len(vot_meta_list)) if vot_results_list[i]["total"] > 50],
        key=lambda i: vot_results_list[i]["margin"]
    )

    latest_indices = canonicalize_indices(latest_candidates)[:10]
    tight_indices = canonicalize_indices(tight_candidates)[:10]
    
    featured_indices = []
    for fid in featured_ids:
        idx = canonical_idx_by_id.get(fid)
        if idx is not None:
            featured_indices.append(idx)

    manifest = {
        "updatedAt": datetime.datetime.now().isoformat(),
        "stats": {
            "diputados": len(diputados_list),
            "votaciones": len(vot_meta_list),
            "votos": sum(len(v) for v in votos_by_leg.values())
        },
        "topTags": sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:20],
        "heroExamples": [
            ["sanidad", "Sanidad CyL"],
            ["infraestructuras", "Soterramiento tren"],
            ["agricultura", "Sector primario"],
            ["cyl", "Todo Castilla y León"]
        ],
        "latestVotes": [get_manifest_vote(i) for i in latest_indices],
        "tightVotes": [get_manifest_vote(i) for i in tight_indices],
        "featuredVotes": [get_manifest_vote(i) for i in featured_indices]
    }

    with open(MANIFEST_FILE, "w") as f:
        json.dump(manifest, f, separators=(',', ':'))

    # 9. Generate votes files
    for leg in LEGISLATURAS:
        if not votos_by_leg[leg]: continue
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
            if a["id"] == "cyl":
                a["legislaturas"] = LEGISLATURAS
                break
        with open(AMBITOS_CONFIG, "w") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
            
    print(f"Transformed {len(vot_meta_list)} total votaciones for {AMBITO}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transforma datos de CyL para frontend.")
    parser.add_argument("--rebuild", action="store_true", help="Regenera todo ignorando overrides existentes.")
    args = parser.parse_args()
    transform(rebuild=args.rebuild)
