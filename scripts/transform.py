#!/usr/bin/env python3
"""
Transforma los JSON brutos del Congreso en votaciones.json para el frontend.
Usa Gemini AI para categorizar los textos parlamentarios con etiquetas múltiples.
"""

import glob
import hashlib
import json
import os
import sys
from google import genai
from google.genai import types
import ai_utils

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(SCRIPT_DIR, "..", "data", "raw")
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "..", "public", "data", "votaciones.json")
CACHE_FILE = os.path.join(SCRIPT_DIR, "..", "data", "cache_categorias.json")
PROMPT_FILE = os.path.join(SCRIPT_DIR, "prompt_categorizacion.txt")
FOTO_MAP_FILE = os.path.join(SCRIPT_DIR, "..", "data", "foto_map.json")
PROVINCIA_MAP_FILE = os.path.join(SCRIPT_DIR, "..", "data", "provincia_map.json")
MANIFEST_FILE = os.path.join(SCRIPT_DIR, "..", "public", "data", "manifest_home.json")
META_FILE = os.path.join(SCRIPT_DIR, "..", "public", "data", "votaciones_meta.json")

VOTE_MAP = {
    "Si": "A favor",
    "Sí": "A favor",
    "No": "En contra",
    "Abstención": "Abstención",
}

LEGISLATURAS = [
    {"id": "X", "desde": "2012-01-01", "hasta": "2015-10-27"},
    {"id": "XI", "desde": "2016-01-13", "hasta": "2016-05-03"},
    {"id": "XII", "desde": "2016-07-19", "hasta": "2019-02-13"},
    {"id": "XIII", "desde": "2019-05-21", "hasta": "2019-09-24"},
    {"id": "XIV", "desde": "2020-01-03", "hasta": "2023-05-29"},
    {"id": "XV", "desde": "2023-08-17", "hasta": "2099-12-31"},
]


def get_leg(fecha):
    """Get legislatura ID for a date string (YYYY-MM-DD)."""
    for leg in reversed(LEGISLATURAS):
        if leg["desde"] <= fecha <= leg["hasta"]:
            return leg["id"]
    return ""


def classify_subgrupo(titulo_subgrupo):
    """Classify a tituloSubGrupo into a short type label."""
    tl = titulo_subgrupo.lower()
    if not titulo_subgrupo:
        return ""
    if "texto d" in tl or "conjunto" in tl:
        return "final"
    if "enmienda" in tl:
        return "enmienda"
    if "sección" in tl or "presupuest" in tl:
        return "presupuestos"
    return "otro"


def text_hash(text):
    return ai_utils.text_hash(text)


def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def parse_congress_date(fecha_str):
    """Convert '26/2/2026' to '2026-02-26'."""
    parts = fecha_str.split("/")
    if len(parts) == 3:
        day, month, year = parts
        return f"{year}-{int(month):02d}-{int(day):02d}"
    return fecha_str


def main():
    skip_ai = "--skip-ai" in sys.argv
    api_key = os.environ.get("GEMINI_API_KEY")

    cache = load_cache()
    # Support both old format (date_S_V.json) and new (Lleg_date_S_V.json)
    raw_files = sorted(
        glob.glob(os.path.join(RAW_DIR, "L*_*_S*_V*.json"))
        + glob.glob(os.path.join(RAW_DIR, "[0-9]*_S*_V*.json"))
    )

    if not raw_files:
        print("No hay archivos JSON en data/raw/")
        return

    print(f"Procesando {len(raw_files)} archivos...")
    BATCH_SIZE = 20
    new_categorizations = 0

    # Each raw file = one unique votación
    votacion_records = []  # list of (votacion_meta, votes)

    # First pass: load all files and collect uncached texts
    file_data_list = []  # (filepath, data, h, texto, titulo_original, fecha)
    uncached = []  # (h, texto) for texts needing AI categorization

    for filepath in raw_files:
        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"  Saltando {os.path.basename(filepath)}: {e}", file=sys.stderr)
            continue

        info = data.get("informacion", {})
        texto = info.get("textoExpediente", "").strip()
        titulo_original = info.get("titulo", "").strip()
        fecha = parse_congress_date(info.get("fecha", ""))
        subgrupo_titulo = info.get("tituloSubGrupo", "").strip()
        subgrupo_texto = info.get("textoSubGrupo", "").strip()
        h = text_hash(texto)

        sesion = info.get("sesion", "")
        numero_votacion = info.get("numeroVotacion", "")
        # Extract legislatura from filename (LXIII_...) or fallback
        basename = os.path.basename(filepath)
        file_leg = ""
        if basename.startswith("L"):
            file_leg = basename.split("_")[0][1:]  # "LXIII_..." -> "XIII"

        file_data_list.append((filepath, data, h, texto, titulo_original, fecha, subgrupo_titulo, subgrupo_texto, sesion, numero_votacion, file_leg))

        if h not in cache:
            if skip_ai or not api_key:
                pass  # Don't pollute cache with fallback entries
            else:
                # Deduplicate: only add each unique hash once
                if not any(uh == h for uh, _ in uncached):
                    uncached.append((h, texto))

    # Batch categorize uncached texts with Gemini
    if uncached and api_key:
        with open(PROMPT_FILE, "r") as f:
            prompt_text = f.read()
            
        total_batches = (len(uncached) + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"  {len(uncached)} textos por categorizar en {total_batches} lotes...")

        for batch_idx in range(0, len(uncached), BATCH_SIZE):
            batch = uncached[batch_idx:batch_idx + BATCH_SIZE]
            batch_num = batch_idx // BATCH_SIZE + 1
            print(f"  Lote {batch_num}/{total_batches} ({len(batch)} textos)...")

            result_map = ai_utils.categorize_batch(batch, api_key, prompt_text)
            for h, cat_data in result_map.items():
                cache[h] = cat_data
                new_categorizations += 1

            # Save cache after each batch (resume-friendly)
            save_cache(cache)

    # Second pass: build votacion records using cache
    # Filter valid categories and tags for frontend indexing
    VALID_CAT_LIST = sorted(list(ai_utils.VALID_CATEGORIES))
    cat_to_idx = {c: i for i, c in enumerate(VALID_CAT_LIST)}

    vot_meta_list = []
    vot_results_list = []
    tag_counts = {}
    
    # Track unique deputies and groups
    dep_fotos = {}
    if os.path.exists(FOTO_MAP_FILE):
        with open(FOTO_MAP_FILE) as f:
            dep_fotos = json.load(f)

    dep_provs = {}
    if os.path.exists(PROVINCIA_MAP_FILE):
        with open(PROVINCIA_MAP_FILE) as f:
            dep_provs = json.load(f)

    unique_diputados = {}
    unique_grupos = set()
    
    # Store votes by legislatura
    votos_by_leg = {}
    vot_detail_by_leg = {}

    for filepath, data, h, texto, titulo_original, fecha, subgrupo_titulo, subgrupo_texto, sesion, numero_votacion, file_leg in file_data_list:
        cat_data = cache.get(h, ai_utils._fallback_categorization())

        titulo_ciudadano = cat_data.get("titulo_ciudadano", "Sin título")
        categoria = cat_data.get("categoria_principal", "Otros")
        etiquetas = cat_data.get("etiquetas", [])
        resumen = cat_data.get("resumen_sencillo", "")
        proponente = cat_data.get("proponente", "")

        leg = file_leg or get_leg(fecha)
        if not leg: continue
        
        if leg not in votos_by_leg:
            votos_by_leg[leg] = []
            vot_detail_by_leg[leg] = {}

        vot_idx = len(vot_meta_list)
        
        favor = 0
        contra = 0
        abstencion = 0
        no_vota = 0
        
        by_group = {}

        for voto_entry in data.get("votaciones", []):
            voto_raw = voto_entry.get("voto", "")
            voto = VOTE_MAP.get(voto_raw, voto_raw)
            
            code = 4
            if voto == "A favor":
                favor += 1
                code = 1
            elif voto == "En contra":
                contra += 1
                code = 2
            elif voto == "Abstención":
                abstencion += 1
                code = 3
            else:
                no_vota += 1
                
            dip_id = voto_entry.get("diputado")
            if not dip_id: continue
            
            grupo = voto_entry.get("grupo")
            unique_grupos.add(grupo)
            
            if dip_id not in unique_diputados:
                unique_diputados[dip_id] = {
                    "nombre": dip_id,
                    "grupo": grupo,
                    "foto": dep_fotos.get(dip_id),
                    "provincia": dep_provs.get(dip_id)
                }
            
            # Store raw vote for later indexing
            votos_by_leg[leg].append([vot_idx, dip_id, grupo, code])
            
            if grupo not in by_group:
                by_group[grupo] = {1: 0, 2: 0, 3: 0, 4: 0}
            by_group[grupo][code] += 1

        total = favor + contra + abstencion
        result = "Aprobada" if favor > contra else ("Rechazada" if contra > favor else "Empate")
        
        vot_meta_list.append({
            "id": f"{leg}-{sesion}-{numero_votacion}",
            "legislatura": leg,
            "fecha": fecha,
            "titulo_ciudadano": titulo_ciudadano,
            "categoria": cat_to_idx.get(categoria, cat_to_idx["Otros"]),
            "etiquetas": etiquetas + ["nacional"]
        })
        
        vot_results_list.append({
            "favor": favor,
            "contra": contra,
            "abstencion": abstencion,
            "total": total,
            "result": result,
            "margin": abs(favor - contra),
            "proponente": proponente
        })
        
        # Calculate group majorities for this vote
        gm = {}
        for g_name, c in by_group.items():
            if c[1] >= c[2] and c[1] >= c[3]: gm[g_name] = 1
            elif c[2] >= c[3]: gm[g_name] = 2
            else: gm[g_name] = 3
        
        vot_detail_by_leg[leg][vot_idx] = {
            "resumen": resumen,
            "textoOficial": titulo_original,
            "urlCongreso": f"https://www.congreso.es/opendata/votaciones?idLegislatura={leg}&idSesion={sesion}&idVotacion={numero_votacion}",
            "subgrupo": classify_subgrupo(subgrupo_titulo),
            "subgrupo_detalle": subgrupo_titulo,
            "group_majority": gm
        }
        
        for t in etiquetas + ["nacional"]:
            tag_counts[t] = tag_counts.get(t, 0) + 1

    # 3. Final indexing and file generation
    sorted_dips = sorted(unique_diputados.keys(), key=lambda x: unique_diputados[x]["nombre"])
    dip_id_to_idx = {d_id: i for i, d_id in enumerate(sorted_dips)}
    
    sorted_grupos = sorted(list(unique_grupos))
    grupo_to_idx = {g: i for i, g in enumerate(sorted_grupos)}
    
    # Update votes with indices
    for leg in votos_by_leg:
        v_list = votos_by_leg[leg]
        for i in range(len(v_list)):
            v_list[i][1] = dip_id_to_idx[v_list[i][1]]
            v_list[i][2] = grupo_to_idx[v_list[i][2]]
            
    # Calculate dip stats
    dip_stats = []
    for d_id in sorted_dips:
        # This would be slow to re-calculate every time from all legs
        # But for now let's do it simply
        stats = {"favor": 0, "contra": 0, "abstencion": 0, "total": 0, "loyal": 0}
        my_legs = set()
        
        for leg in votos_by_leg:
            for v in votos_by_leg[leg]:
                if sorted_dips[v[1]] == d_id:
                    code = v[3]
                    if code == 1: stats["favor"] += 1
                    elif code == 2: stats["contra"] += 1
                    elif code == 3: stats["abstencion"] += 1
                    
                    if code in (1, 2, 3):
                        stats["total"] += 1
                        my_legs.add(leg)
                        # Check loyalty
                        gm = vot_detail_by_leg[leg][v[0]]["group_majority"]
                        if gm.get(sorted_grupos[v[2]]) == code:
                            stats["loyal"] += 1
                            
        dip_stats.append({
            "favor": stats["favor"],
            "contra": stats["contra"],
            "abstencion": stats["abstencion"],
            "total": stats["total"],
            "mainGrupo": grupo_to_idx[unique_diputados[d_id]["grupo"]],
            "loyalty": round(stats["loyal"] / stats["total"], 4) if stats["total"] > 0 else 0,
            "legislaturas": list(my_legs)
        })

    # Group affinity
    group_affinity_by_leg = {}
    for leg_id in list(votos_by_leg.keys()) + [""]:
        ga = {}
        for vi in range(len(vot_meta_list)):
            if leg_id and vot_meta_list[vi]["legislatura"] != leg_id: continue
            
            # Get group majority from detail
            found_leg = vot_meta_list[vi]["legislatura"]
            gm = vot_detail_by_leg[found_leg][vi]["group_majority"]
            
            g_keys = sorted(gm.keys())
            for a in range(len(g_keys)):
                for b in range(a + 1, len(g_keys)):
                    ga_idx, gb_idx = grupo_to_idx[g_keys[a]], grupo_to_idx[g_keys[b]]
                    key = f"{ga_idx},{gb_idx}" if ga_idx < gb_idx else f"{gb_idx},{ga_idx}"
                    if key not in ga: ga[key] = {"same": 0, "total": 0}
                    ga[key]["total"] += 1
                    if gm[g_keys[a]] == gm[g_keys[b]]: ga[key]["same"] += 1
        if ga: group_affinity_by_leg[leg_id] = ga

    meta = {
        "diputados": [unique_diputados[d_id]["nombre"] for d_id in sorted_dips],
        "grupos": sorted_grupos,
        "categorias": VALID_CAT_LIST,
        "votaciones": vot_meta_list,
        "votResults": vot_results_list,
        "tagCounts": tag_counts,
        "topTags": sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:30],
        "sortedVotIdxByDate": list(range(len(vot_meta_list))),
        "dipStats": dip_stats,
        "groupAffinityByLeg": group_affinity_by_leg,
        "votsByExp": {}, # Optional for now
        "votIdById": {v["id"]: i for i, v in enumerate(vot_meta_list)},
        "dipFotos": [unique_diputados[d_id]["foto"] for d_id in sorted_dips],
        "dipProvincias": [unique_diputados[d_id]["provincia"] for d_id in sorted_dips]
    }

    with open(META_FILE, "w") as f:
        json.dump(meta, f, separators=(',', ':'))

    # Featured votes
    FEATURED_FILE = os.path.join(SCRIPT_DIR, "..", "data", "featured_votes.json")
    featured_ids = []
    if os.path.exists(FEATURED_FILE):
        with open(FEATURED_FILE, "r") as f:
            featured_ids = json.load(f).get("nacional", [])

    def get_manifest_vote(idx):
        v_meta = vot_meta_list[idx]
        v_res = vot_results_list[idx]
        return {
            "id": v_meta["id"],
            "titulo_ciudadano": v_meta["titulo_ciudadano"],
            "fecha": v_meta["fecha"],
            "categoria": VALID_CAT_LIST[v_meta["categoria"]],
            "etiquetas": v_meta["etiquetas"],
            "subTipo": vot_detail_by_leg[v_meta["legislatura"]][idx].get("subgrupo", ""),
            "proponente": v_res.get("proponente", ""),
            "result": v_res["result"],
            "favor": v_res["favor"],
            "contra": v_res["contra"],
            "abstencion": v_res["abstencion"],
            "total": v_res["total"],
            "margin": v_res["margin"]
        }

    latest_indices = sorted(range(len(vot_meta_list)), key=lambda i: (vot_meta_list[i]["fecha"], i), reverse=True)[:10]
    tight_indices = sorted([i for i in range(len(vot_meta_list)) if vot_results_list[i]["total"] > 300], 
                          key=lambda i: vot_results_list[i]["margin"])[:10]
    
    featured_indices = []
    for fid in featured_ids:
        for i, v in enumerate(vot_meta_list):
            if v["id"] == fid:
                featured_indices.append(i)
                break

    manifest = {
        "stats": {
            "diputados": len(sorted_dips),
            "votaciones": len(vot_meta_list),
            "votos": sum(len(v) for v in votos_by_leg.values())
        },
        "topTags": sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:20],
        "heroExamples": [
            ["subir_pensiones", "Quien voto subir pensiones?"],
            ["facilitar_acceso_vivienda", "Acceso a vivienda"],
            ["combatir_cambio_climatico", "Cambio climatico"],
            ["reformar_codigo_penal", "Reforma penal"],
            ["proteger_sanidad_publica", "Sanidad publica"]
        ],
        "latestVotes": [get_manifest_vote(i) for i in latest_indices],
        "tightVotes": [get_manifest_vote(i) for i in tight_indices],
        "featuredVotes": [get_manifest_vote(i) for i in featured_indices]
    }

    with open(MANIFEST_FILE, "w") as f:
        json.dump(manifest, f, separators=(',', ':'))

    print(f"Transformación completada: {len(vot_meta_list)} votaciones.")

if __name__ == "__main__":
    main()
