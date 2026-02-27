#!/usr/bin/env python3
"""
Transforma los JSON brutos del Congreso en votaciones.json para el frontend.
Usa gemini-cli para categorizar los textos parlamentarios con etiquetas múltiples.
"""

import glob
import hashlib
import json
import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(SCRIPT_DIR, "..", "data", "raw")
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "..", "data", "votaciones.json")
CACHE_FILE = os.path.join(SCRIPT_DIR, "..", "data", "cache_categorias.json")
PROMPT_FILE = os.path.join(SCRIPT_DIR, "prompt_categorizacion.txt")

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
    """Categorize a batch of parliamentary texts using claude CLI.

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
    items_block = "\n".join(batch_items)

    full_prompt = (
        f"{prompt_template}\n\n"
        f"Categoriza CADA uno de los siguientes {len(texts_with_hashes)} asuntos parlamentarios.\n"
        f"Devuelve un JSON array con un objeto por asunto, en el MISMO ORDEN.\n"
        f"SOLO el JSON array, sin markdown ni explicacion.\n\n"
        f"{items_block}"
    )

    try:
        env = os.environ.copy()
        env.pop("CLAUDECODE", None)

        result = subprocess.run(
            ["claude", "-p", "--model", "haiku", "--output-format", "text"],
            input=full_prompt,
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )

        output = result.stdout.strip()

        if not output:
            raise ValueError(f"Empty output (rc={result.returncode}): {result.stderr[:200]}")

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
        h = text_hash(texto)

        file_data_list.append((filepath, data, h, texto, titulo_original, fecha))

        if h not in cache:
            if skip_ai:
                cat_data = _fallback_categorization()
                cat_data["titulo_ciudadano"] = titulo_original[:60] if titulo_original else "Sin título"
                cache[h] = cat_data
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
    for filepath, data, h, texto, titulo_original, fecha in file_data_list:
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

    # Each votacion_record is already a unique votación (one per raw file)
    votaciones_list = []
    votos_list = []

    for vot_idx, (meta, votes) in enumerate(votacion_records):
        votaciones_list.append({
            "fecha": meta["fecha"],
            "titulo_ciudadano": meta["titulo_ciudadano"],
            "categoria": cat_idx[meta["categoria_principal"]],
            "etiquetas": meta.get("etiquetas", []),
            "resumen": meta.get("resumen", ""),
            "proponente": meta.get("proponente", ""),
        })
        for v in votes:
            votos_list.append([
                vot_idx,
                dip_idx[v["diputado"]],
                grp_idx[v["grupo"]],
                voto_code[v["voto"]],
            ])

    output = {
        "meta": {
            "generado": __import__("datetime").date.today().isoformat(),
            "total_votaciones": len(votaciones_list),
            "total_votos": len(votos_list),
        },
        "diputados": diputados_set,
        "grupos": grupos_set,
        "categorias": categorias_set,
        "votaciones": votaciones_list,
        "votos": votos_list,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, separators=(",", ":"))

    save_cache(cache)

    print(f"\nCompletado:")
    print(f"  {len(votaciones_list)} votaciones únicas")
    print(f"  {len(votos_list)} votos individuales")
    print(f"  {len(diputados_set)} diputados")
    print(f"  {len(grupos_set)} grupos")
    print(f"Nuevas categorizaciones: {new_categorizations}")
    print(f"Entradas en caché: {len(cache)}")


if __name__ == "__main__":
    main()
