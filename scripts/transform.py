#!/usr/bin/env python3
"""
Transforma los JSON brutos del Congreso en votaciones.json para el frontend.
Usa gemini-cli para categorizar los textos parlamentarios con etiquetas múltiples.
"""

import glob
import hashlib
import json
import os
import json
import os
import sys
from google import genai
from google.genai import types
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(SCRIPT_DIR, "..", "data", "raw")
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "..", "public", "data", "votaciones.json")
CACHE_FILE = os.path.join(SCRIPT_DIR, "..", "data", "cache_categorias.json")
PROMPT_FILE = os.path.join(SCRIPT_DIR, "prompt_categorizacion.txt")
FOTO_MAP_FILE = os.path.join(SCRIPT_DIR, "..", "data", "foto_map.json")
MANIFEST_FILE = os.path.join(SCRIPT_DIR, "..", "public", "data", "manifest_home.json")
META_FILE = os.path.join(SCRIPT_DIR, "..", "public", "data", "votaciones_meta.json")

VALID_CATEGORIES = frozenset([
    "Economia_y_Hacienda", "Sanidad", "Educacion", "Vivienda",
    "Trabajo_y_Pensiones", "Derechos_Sociales", "Justicia",
    "Interior_y_Seguridad", "Medio_Ambiente", "Infraestructuras",
    "Politica_Territorial", "Asuntos_Exteriores", "Gobernanza",
    "Agricultura", "Cultura", "Otros",
    # Legacy names with accents (accept but normalize)
    "Economía_y_Hacienda", "Educación",
])

# Normalize accented category names to non-accented
CATEGORY_NORMALIZE = {
    "Economía_y_Hacienda": "Economia_y_Hacienda",
    "Educación": "Educacion",
}

VALID_TAGS = frozenset([
    # Procedimiento parlamentario
    "procedimiento_parlamentario", "tramitar_ley_urgencia",
    "crear_comision_investigacion", "reformar_reglamento_congreso",
    "aprobar_acuerdo_internacional",
    # Control al gobierno
    "controlar_gobierno", "exigir_responsabilidades_gobierno",
    "reprobar_gestion_gobierno",
    # Presupuestos y finanzas
    "aprobar_presupuestos", "controlar_gasto_publico",
    "reducir_deficit", "limitar_deuda_publica",
    # Impuestos
    "subir_impuestos", "bajar_impuestos", "combatir_fraude_fiscal",
    # Economia
    "impulsar_crecimiento_economico", "apoyar_emprendedores",
    "proteger_consumidores", "regular_sector_financiero",
    # Empleo
    "crear_empleo", "mejorar_condiciones_laborales",
    "reducir_jornada_laboral", "proteger_trabajadores",
    # Pensiones
    "subir_pensiones", "reformar_pensiones", "garantizar_pensiones",
    # Conciliacion y seguridad social
    "impulsar_conciliacion", "reformar_seguridad_social",
    # Sanidad
    "proteger_sanidad_publica", "ampliar_sanidad_publica",
    "mejorar_salud_mental", "proteger_enfermos", "legalizar_eutanasia",
    # Educacion
    "reformar_educacion", "proteger_educacion_publica",
    "financiar_universidad", "impulsar_formacion_profesional",
    "impulsar_ciencia",
    # Vivienda
    "facilitar_acceso_vivienda", "evitar_desahucios",
    "proteger_inquilinos", "limitar_okupacion",
    # Igualdad y genero
    "combatir_violencia_machista", "impulsar_igualdad_genero",
    "proteger_derechos_lgbti",
    # Derechos sociales
    "combatir_pobreza", "proteger_infancia", "proteger_familias",
    "proteger_personas_discapacidad", "proteger_derechos_humanos",
    "proteger_libertad_expresion",
    # Inmigracion
    "restringir_inmigracion", "regularizar_inmigrantes",
    "proteger_refugiados",
    # Justicia
    "reformar_codigo_penal", "reformar_poder_judicial",
    "reformar_tribunal_constitucional", "combatir_corrupcion",
    "recuperar_memoria_historica",
    # Seguridad
    "aumentar_seguridad_ciudadana", "combatir_terrorismo",
    "proteger_victimas_terrorismo", "mejorar_seguridad_vial",
    # Medio ambiente
    "combatir_cambio_climatico", "reducir_emisiones",
    "proteger_medio_ambiente", "gestionar_recursos_hidricos",
    "proteger_biodiversidad",
    # Energia
    "impulsar_energia_renovable", "garantizar_suministro_electrico",
    "combatir_pobreza_energetica",
    # Infraestructuras
    "mejorar_red_ferroviaria", "mejorar_carreteras",
    "fomentar_transporte_publico", "financiar_infraestructuras",
    "impulsar_telecomunicaciones",
    # Territorio
    "financiar_autonomias", "financiar_ayuntamientos",
    "combatir_despoblacion", "reformar_financiacion_autonomica",
    # Asuntos exteriores
    "adaptar_normativa_europea", "impulsar_cooperacion_internacional",
    "aumentar_gasto_defensa", "reducir_gasto_defensa",
    "apoyar_palestina",
    # Agricultura
    "proteger_sector_primario", "defender_agricultores",
    # Gobernanza
    "aumentar_transparencia", "regular_lobbies",
    "reformar_ley_electoral", "apoyar_monarquia", "abolir_monarquia",
    # Emergencias
    "aprobar_ayudas_emergencia", "financiar_reconstruccion",
    # Cultura
    "impulsar_cultura", "reformar_medios_comunicacion",
    "proteger_lenguas_cooficiales",
])

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
    if "totalidad" in tl:
        return "totalidad"
    if "transaccion" in tl:
        return "transaccional"
    if "voto particular" in tl or "votos particulares" in tl:
        return "particular"
    if "enmienda" in tl:
        return "enmienda"
    if "separada" in tl or "punto" in tl:
        return "separada"
    if "dictamen" in tl:
        return "dictamen"
    if "propuesta" in tl:
        return "propuesta"
    return "otro"


def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def text_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def categorize_batch(texts_with_hashes):
    """Categorize a batch of parliamentary texts using google-genai.

    Args:
        texts_with_hashes: list of (hash, text_expediente) tuples

    Returns:
        dict mapping hash -> categorization data
    """
    with open(PROMPT_FILE, encoding="utf-8") as f:
        prompt_template = f.read()

    # Build batch prompt
    batch_items = []
    for i, (h, text) in enumerate(texts_with_hashes):
        batch_items.append(f'[{i}] "{text}"')
    items_block = "\\n".join(batch_items)

    full_prompt = (
        f"{prompt_template}\\n\\n"
        f"Categoriza CADA uno de los siguientes {len(texts_with_hashes)} asuntos parlamentarios.\\n"
        f"Devuelve un JSON array con un objeto por asunto, en el MISMO ORDEN.\\n"
        f"SOLO el JSON array, sin markdown ni explicacion.\\n\\n"
        f"{items_block}"
    )

    try:
        # Initialize the client. It will automatically pick up GEMINI_API_KEY from the environment
        client = genai.Client()
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=full_prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
            )
        )

        output = response.text.strip()

        if not output:
            raise ValueError("Empty output from Gemini")

        # Extract JSON from possible markdown fences
        if "```json" in output:
            output = output.split("```json")[1].split("```")[0].strip()
        elif "```" in output:
            output = output.split("```")[1].split("```")[0].strip()

        results_list = json.loads(output)

        if not isinstance(results_list, list):
            raise ValueError(f"Expected JSON array, got {type(results_list).__name__}")

        result_map = {}
        for i, (h, _text) in enumerate(texts_with_hashes):
            if i < len(results_list):
                data = _validate_categorization(results_list[i])
            else:
                data = _fallback_categorization()
            result_map[h] = data

        return result_map

    except Exception as e:
        print(f"  Batch error: {e}", file=sys.stderr)
        result_map = {}
        for h, text in texts_with_hashes:
            result_map[h] = _fallback_categorization()
        return result_map

def _validate_categorization(data):
    """Validate and normalize a single categorization result."""
    if not isinstance(data, dict):
        return _fallback_categorization()

    cat = data.get("categoria_principal", "Otros")
    cat = CATEGORY_NORMALIZE.get(cat, cat)
    if cat not in VALID_CATEGORIES:
        cat = "Otros"
    data["categoria_principal"] = cat

    words = data.get("titulo_ciudadano", "").split()
    if len(words) > 12:
        data["titulo_ciudadano"] = " ".join(words[:12])

    etiquetas = data.get("etiquetas", [])
    if not isinstance(etiquetas, list):
        etiquetas = []
    # Filter to only valid tags from the constrained vocabulary
    etiquetas = [t for t in etiquetas if t in VALID_TAGS]
    data["etiquetas"] = etiquetas[:4]

    if not data.get("resumen_sencillo"):
        data["resumen_sencillo"] = ""

    if not data.get("proponente"):
        data["proponente"] = ""

    return data


def _fallback_categorization():
    return {
        "titulo_ciudadano": "Asunto parlamentario sin clasificar",
        "categoria_principal": "Otros",
        "etiquetas": [],
        "resumen_sencillo": "",
        "proponente": "",
    }


def parse_congress_date(fecha_str):
    """Convert '26/2/2026' to '2026-02-26'."""
    parts = fecha_str.split("/")
    if len(parts) == 3:
        day, month, year = parts
        return f"{year}-{int(month):02d}-{int(day):02d}"
    return fecha_str


def main():
    skip_ai = "--skip-ai" in sys.argv

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
            if skip_ai:
                pass  # Don't pollute cache with fallback entries
            else:
                # Deduplicate: only add each unique hash once
                if not any(uh == h for uh, _ in uncached):
                    uncached.append((h, texto))

    # Batch categorize uncached texts with Gemini
    if uncached:
        total_batches = (len(uncached) + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"  {len(uncached)} textos por categorizar en {total_batches} lotes...")

        for batch_idx in range(0, len(uncached), BATCH_SIZE):
            batch = uncached[batch_idx:batch_idx + BATCH_SIZE]
            batch_num = batch_idx // BATCH_SIZE + 1
            print(f"  Lote {batch_num}/{total_batches} ({len(batch)} textos)...")

            result_map = categorize_batch(batch)
            for h, cat_data in result_map.items():
                cache[h] = cat_data
                new_categorizations += 1

            # Save cache after each batch (resume-friendly)
            save_cache(cache)

    # Second pass: build votacion records using cache
    for filepath, data, h, texto, titulo_original, fecha, subgrupo_titulo, subgrupo_texto, sesion, numero_votacion, file_leg in file_data_list:
        cat_data = cache.get(h, _fallback_categorization())

        titulo_ciudadano = cat_data.get("titulo_ciudadano", "Sin título")
        categoria = cat_data.get("categoria_principal", "Otros")
        etiquetas = cat_data.get("etiquetas", [])
        resumen = cat_data.get("resumen_sencillo", "")
        proponente = cat_data.get("proponente", "")

        votes = []
        for voto_entry in data.get("votaciones", []):
            voto_raw = voto_entry.get("voto", "")
            voto = VOTE_MAP.get(voto_raw, voto_raw)
            if voto not in ("A favor", "En contra", "Abstención"):
                continue

            grupo = voto_entry.get("grupo", "").strip()
            votes.append({
                "diputado": voto_entry.get("diputado", ""),
                "grupo": grupo if grupo else "Sin grupo",
                "voto": voto,
            })

        if votes:
            votacion_records.append((
                {
                    "fecha": fecha,
                    "titulo_ciudadano": titulo_ciudadano,
                    "categoria_principal": categoria,
                    "etiquetas": etiquetas,
                    "resumen": resumen,
                    "proponente": proponente,
                    "subgrupo_titulo": subgrupo_titulo,
                    "subgrupo_texto": subgrupo_texto,
                    "exp_hash": text_hash(texto),
                    "texto_oficial": texto,
                    "sesion": sesion,
                    "numero_votacion": numero_votacion,
                    "legislatura": file_leg,
                },
                votes,
            ))

    # ── Normalize for compact output ──
    # Build lookup tables from all votes
    all_diputados = set()
    all_grupos = set()
    all_categorias = set()
    for meta, votes in votacion_records:
        all_categorias.add(meta["categoria_principal"])
        for v in votes:
            all_diputados.add(v["diputado"])
            all_grupos.add(v["grupo"])

    diputados_set = sorted(all_diputados)
    grupos_set = sorted(all_grupos)
    categorias_set = sorted(all_categorias)

    dip_idx = {name: i for i, name in enumerate(diputados_set)}
    grp_idx = {name: i for i, name in enumerate(grupos_set)}
    cat_idx = {name: i for i, name in enumerate(categorias_set)}

    voto_code = {"A favor": 1, "En contra": 2, "Abstención": 3}

    # ── Group votaciones by textoExpediente ──
    # Build expediente groups: texto_hash -> list of votacion_record indices
    exp_groups = {}
    for rec_idx, (meta, _votes) in enumerate(votacion_records):
        eh = meta.get("exp_hash", "")
        if eh:
            if eh not in exp_groups:
                exp_groups[eh] = []
            exp_groups[eh].append(rec_idx)

    # Only keep groups with >1 votacion
    multi_exp = {eh: indices for eh, indices in exp_groups.items() if len(indices) > 1}
    print(f"  Expedientes con múltiples votaciones: {len(multi_exp)}")

    # Each votacion_record is already a unique votación (one per raw file)
    votaciones_list = []
    votos_list = []

    for vot_idx, (meta, votes) in enumerate(votacion_records):
        votacion_entry = {
            "fecha": meta["fecha"],
            "titulo_ciudadano": meta["titulo_ciudadano"],
            "categoria": cat_idx[meta["categoria_principal"]],
            "etiquetas": meta.get("etiquetas", []),
            "resumen": meta.get("resumen", ""),
            "proponente": meta.get("proponente", ""),
        }
        if meta.get("subgrupo_titulo"):
            votacion_entry["subgrupo"] = meta["subgrupo_titulo"]
        if meta.get("subgrupo_texto") and meta.get("subgrupo_texto") != meta.get("subgrupo_titulo"):
            votacion_entry["subgrupo_detalle"] = meta["subgrupo_texto"]

        # Add expediente group info for multi-vote groups
        eh = meta.get("exp_hash", "")
        sub_tipo = classify_subgrupo(meta.get("subgrupo_titulo", ""))
        if eh and eh in multi_exp:
            votacion_entry["exp"] = eh
            if sub_tipo:
                votacion_entry["subTipo"] = sub_tipo

        # Official text and congreso.es link
        if meta.get("texto_oficial"):
            votacion_entry["textoOficial"] = meta["texto_oficial"]
        if meta.get("sesion") and meta.get("numero_votacion") and meta.get("legislatura"):
            votacion_entry["urlCongreso"] = (
                f"https://www.congreso.es/opendata/votaciones"
                f"?idLegislatura={meta['legislatura']}"
                f"&idSesion={meta['sesion']}"
                f"&idVotacion={meta['numero_votacion']}"
            )

        # Stable ID for URLs: legislatura-sesion-numero
        _leg = meta.get("legislatura", "")
        _ses = meta.get("sesion", "")
        _num = meta.get("numero_votacion", "")
        if _leg and _ses and _num:
            votacion_entry["id"] = f"{_leg}-{_ses}-{_num}"
        else:
            votacion_entry["id"] = f"h_{text_hash(meta.get('texto_oficial', '') or str(vot_idx))[:8]}"

        votaciones_list.append(votacion_entry)
        for v in votes:
            votos_list.append([
                vot_idx,
                dip_idx[v["diputado"]],
                grp_idx[v["grupo"]],
                voto_code[v["voto"]],
            ])

    # ── Load foto_map and build dipFotos ──
    dip_fotos = [None] * len(diputados_set)
    if os.path.exists(FOTO_MAP_FILE):
        with open(FOTO_MAP_FILE, encoding="utf-8") as f:
            foto_map = json.load(f)
        foto_lookup = {}
        for full_name, leg_map in foto_map.items():
            foto_lookup[full_name.lower()] = leg_map

        matched_fotos = 0
        for i, dip_name in enumerate(diputados_set):
            if ", " in dip_name:
                apellidos, nombre = dip_name.split(", ", 1)
                congreso_key = f"{nombre} {apellidos}".lower()
                if congreso_key in foto_lookup:
                    dip_fotos[i] = foto_lookup[congreso_key]
                    matched_fotos += 1
        print(f"  Fotos mapeadas: {matched_fotos}/{len(diputados_set)}")
    else:
        print("  (sin foto_map.json, ejecuta scrape_photos.py)")

    # ── Add legislatura to each votacion ──
    for vi in range(len(votaciones_list)):
        votaciones_list[vi]["legislatura"] = get_leg(votaciones_list[vi]["fecha"])

    # ── Pre-compute: build vote indexes ──
    print("  Pre-computando índices...")
    vbv = {}  # votIdx -> list of votos indices
    vbd = {}  # dipIdx -> list of votos indices
    for i, v in enumerate(votos_list):
        vbv.setdefault(v[0], []).append(i)
        vbd.setdefault(v[1], []).append(i)

    # ── Pre-compute: votacion results + group majorities ──
    vot_results = []
    group_majority = {}
    for vi in range(len(votaciones_list)):
        indices = vbv.get(vi, [])
        t = {1: 0, 2: 0, 3: 0}
        by_group = {}
        for j in indices:
            v = votos_list[j]
            code, grp = v[3], v[2]
            t[code] += 1
            if grp not in by_group:
                by_group[grp] = {1: 0, 2: 0, 3: 0}
            by_group[grp][code] += 1

        total = len(indices)
        favor, contra = t[1], t[2]
        result = "Aprobada" if favor > contra else ("Rechazada" if contra > favor else "Empate")
        vot_results.append({
            "favor": favor,
            "contra": contra,
            "abstencion": t[3],
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
        group_majority[vi] = gm

    # ── Pre-compute: diputado stats + loyalty ──
    print("  Pre-computando stats de diputados...")
    leg_ids = [l["id"] for l in LEGISLATURAS]
    dip_stats = []
    for di in range(len(diputados_set)):
        indices = vbd.get(di, [])
        t = {1: 0, 2: 0, 3: 0}
        grupo_count = {}
        loyal = 0
        for j in indices:
            v = votos_list[j]
            code, grp = v[3], v[2]
            t[code] += 1
            grupo_count[grp] = grupo_count.get(grp, 0) + 1
            maj = group_majority.get(v[0], {})
            if maj.get(grp) == code:
                loyal += 1

        total = len(indices)
        main_grupo = -1
        if grupo_count:
            main_grupo = max(grupo_count, key=grupo_count.get)

        leg_set = set()
        for j in indices:
            leg = votaciones_list[votos_list[j][0]].get("legislatura", "")
            if leg:
                leg_set.add(leg)

        dip_stats.append({
            "favor": t[1],
            "contra": t[2],
            "abstencion": t[3],
            "total": total,
            "mainGrupo": main_grupo,
            "loyalty": round(loyal / total, 4) if total > 0 else 0,
            "legislaturas": [lid for lid in leg_ids if lid in leg_set],
        })

    # ── Pre-compute: tag counts ──
    tag_counts = {}
    for vot in votaciones_list:
        for tag in vot.get("etiquetas", []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    top_tags = sorted(tag_counts.items(), key=lambda x: -x[1])[:20]

    # ── Pre-compute: sorted votacion indices by date desc ──
    sorted_vot_idx = sorted(
        range(len(votaciones_list)),
        key=lambda i: votaciones_list[i]["fecha"],
        reverse=True,
    )

    # ── Pre-compute: group affinity by legislatura ──
    print("  Pre-computando afinidad entre grupos...")
    group_affinity_by_leg = {}
    for leg_id in leg_ids + [""]:
        ga = {}
        for vi in range(len(votaciones_list)):
            if leg_id and votaciones_list[vi].get("legislatura") != leg_id:
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

    # ── Pre-compute: votaciones by expediente ──
    vots_by_exp = {}
    for i, vot in enumerate(votaciones_list):
        exp = vot.get("exp")
        if exp:
            vots_by_exp.setdefault(exp, []).append(i)

    # ── Pre-compute: votacion id to index mapping ──
    votIdById = {vot["id"]: i for i, vot in enumerate(votaciones_list)}

    # ══════════════════════════════════════════════
    # Generate Tier 1: manifest_home.json
    # ══════════════════════════════════════════════
    hero_examples = [
        ["subir_pensiones", "Quien voto subir pensiones?"],
        ["facilitar_acceso_vivienda", "Acceso a vivienda"],
        ["combatir_cambio_climatico", "Cambio climatico"],
        ["reformar_codigo_penal", "Reforma penal"],
        ["proteger_sanidad_publica", "Sanidad publica"],
    ]
    hero_examples = [e for e in hero_examples if e[0] in tag_counts]

    latest_votes = sorted_vot_idx[:10]
    tight_votes = sorted(
        [i for i in sorted_vot_idx if vot_results[i]["total"] > 0],
        key=lambda i: vot_results[i]["margin"],
    )[:10]
    rebels = sorted(
        [i for i in range(len(diputados_set)) if dip_stats[i]["total"] > 50],
        key=lambda i: dip_stats[i]["loyalty"],
    )[:10]

    def manifest_vote(vi):
        v = votaciones_list[vi]
        r = vot_results[vi]
        return {
            "id": v["id"],
            "titulo_ciudadano": v["titulo_ciudadano"],
            "fecha": v["fecha"],
            "categoria": categorias_set[v["categoria"]],
            "etiquetas": v.get("etiquetas", []),
            "subTipo": v.get("subTipo", ""),
            "proponente": v.get("proponente", ""),
            "result": r["result"],
            "favor": r["favor"],
            "contra": r["contra"],
            "abstencion": r["abstencion"],
            "total": r["total"],
            "margin": r["margin"],
        }

    manifest = {
        "stats": {
            "diputados": len(diputados_set),
            "votaciones": len(votaciones_list),
            "votos": len(votos_list),
        },
        "topTags": [list(t) for t in top_tags],
        "heroExamples": hero_examples,
        "latestVotes": [manifest_vote(i) for i in latest_votes],
        "tightVotes": [manifest_vote(i) for i in tight_votes],
        "rebels": [
            {
                "name": diputados_set[i],
                "grupo": grupos_set[dip_stats[i]["mainGrupo"]] if dip_stats[i]["mainGrupo"] >= 0 else "Sin grupo",
                "loyalty": round(dip_stats[i]["loyalty"], 4),
            }
            for i in rebels
        ],
        "categorias": categorias_set,
    }

    # ══════════════════════════════════════════════
    # Generate Tier 2: votaciones_meta.json
    # ══════════════════════════════════════════════
    # Strip heavy detail-only fields from tier 2 (saved ~5.8 MB)
    DETAIL_FIELDS = {"textoOficial", "resumen", "urlCongreso", "subgrupo", "subgrupo_detalle"}
    votaciones_light = [
        {k: v for k, v in vot.items() if k not in DETAIL_FIELDS}
        for vot in votaciones_list
    ]

    meta_output = {
        "meta": {
            "generado": __import__("datetime").date.today().isoformat(),
            "total_votaciones": len(votaciones_list),
            "total_votos": len(votos_list),
        },
        "diputados": diputados_set,
        "grupos": grupos_set,
        "categorias": categorias_set,
        "dipFotos": dip_fotos,
        "votaciones": votaciones_light,
        "votResults": vot_results,
        "dipStats": dip_stats,
        "tagCounts": tag_counts,
        "topTags": [list(t) for t in top_tags],
        "sortedVotIdxByDate": sorted_vot_idx,
        "groupAffinityByLeg": group_affinity_by_leg,
        "votsByExp": vots_by_exp,
        "votIdById": votIdById,
    }

    # ══════════════════════════════════════════════
    # Generate Tier 3: votos_{leg}.json per legislatura
    # Includes individual votes + detail fields for VotacionDetail
    # ══════════════════════════════════════════════
    votos_by_leg = {}
    detail_by_leg = {}
    for v in votos_list:
        leg = votaciones_list[v[0]].get("legislatura", "")
        if leg:
            votos_by_leg.setdefault(leg, []).append(v)

    for i, vot in enumerate(votaciones_list):
        leg = vot.get("legislatura", "")
        detail = {k: vot[k] for k in DETAIL_FIELDS if k in vot and vot[k]}
        if leg and detail:
            detail_by_leg.setdefault(leg, {})[i] = detail

    # ── Write all output files ──
    output_dir = os.path.dirname(OUTPUT_FILE)
    os.makedirs(output_dir, exist_ok=True)

    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, separators=(",", ":"))

    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(meta_output, f, ensure_ascii=False, separators=(",", ":"))

    for leg_id, leg_votos in votos_by_leg.items():
        votos_file = os.path.join(output_dir, f"votos_{leg_id}.json")
        tier3 = {"votos": leg_votos, "detail": detail_by_leg.get(leg_id, {})}
        with open(votos_file, "w", encoding="utf-8") as f:
            json.dump(tier3, f, ensure_ascii=False, separators=(",", ":"))

    # Remove old backward-compat file if it exists
    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)
        print(f"  Eliminado {os.path.basename(OUTPUT_FILE)} (ya no se usa)")

    save_cache(cache)

    # ── Print summary ──
    manifest_size = os.path.getsize(MANIFEST_FILE) / 1024
    meta_size = os.path.getsize(META_FILE) / (1024 * 1024)
    print(f"\nCompletado:")
    print(f"  {len(votaciones_list)} votaciones únicas")
    print(f"  {len(votos_list)} votos individuales")
    print(f"  {len(diputados_set)} diputados")
    print(f"  {len(grupos_set)} grupos")
    print(f"  manifest_home.json: {manifest_size:.1f} KB")
    print(f"  votaciones_meta.json: {meta_size:.1f} MB")
    for leg_id in sorted(votos_by_leg.keys()):
        votos_file = os.path.join(output_dir, f"votos_{leg_id}.json")
        votos_size = os.path.getsize(votos_file) / (1024 * 1024)
        print(f"  votos_{leg_id}.json: {votos_size:.1f} MB ({len(votos_by_leg[leg_id])} votos)")
    print(f"Nuevas categorizaciones: {new_categorizations}")
    print(f"Entradas en caché: {len(cache)}")


if __name__ == "__main__":
    main()
