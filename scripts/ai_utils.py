import hashlib
import json
import os
import sys
import re
import subprocess
from google import genai
from google.genai import types

VALID_CATEGORIES = frozenset([
    "Economia_y_Hacienda", "Sanidad", "Educacion", "Vivienda",
    "Trabajo_y_Pensiones", "Derechos_Sociales", "Justicia",
    "Interior_y_Seguridad", "Medio_Ambiente", "Infraestructuras",
    "Politica_Territorial", "Asuntos_Exteriores", "Gobernanza",
    "Agricultura", "Cultura", "Otros",
])

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
    # Territorio y CCAA
    "financiar_autonomias", "financiar_ayuntamientos",
    "combatir_despoblacion", "reformar_financiacion_autonomica",
    "reformar_estatuto_autonomia", "reclamar_competencias",
    "reclamar_financiacion_estatal", "impulsar_desarrollo_rural",
    "combatir_despoblacion_local", "promover_turismo_regional",
    "mejorar_atencion_dependencia", "gestionar_recursos_hidricos_locales",
    "proteger_patrimonio_historico", "proteger_lengua_propia",
    "promover_cultura_local",
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
    # Instituciones
    "nacional", "andalucia", "cyl", "madrid",
])

def text_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

def _validate_categorization(data):
    if not isinstance(data, dict):
        return _fallback_categorization()

    cat = data.get("categoria_principal", "Otros")
    cat = CATEGORY_NORMALIZE.get(cat, cat)
    if cat not in VALID_CATEGORIES:
        cat = "Otros"
    data["categoria_principal"] = cat

    words = data.get("titulo_ciudadano", "").split()
    if len(words) > 15:
        data["titulo_ciudadano"] = " ".join(words[:15])

    etiquetas = data.get("etiquetas", [])
    if not isinstance(etiquetas, list):
        etiquetas = []
    etiquetas = [t for t in etiquetas if t in VALID_TAGS]
    data["etiquetas"] = etiquetas[:4]

    if not data.get("resumen_sencillo"):
        data["resumen_sencillo"] = ""

    return data

def _fallback_categorization():
    return {
        "titulo_ciudadano": "Asunto parlamentario sin clasificar",
        "categoria_principal": "Otros",
        "etiquetas": [],
        "resumen_sencillo": "",
        "proponente": "",
    }

def categorize_batch(texts_with_ids, api_key, prompt_text):
    """
    texts_with_ids: list of (id, text)
    """
    if api_key:
        return _categorize_batch_sdk(texts_with_ids, api_key, prompt_text)
    else:
        return _categorize_batch_cli(texts_with_ids, prompt_text)

def _categorize_batch_sdk(texts_with_ids, api_key, prompt_text):
    client = genai.Client(api_key=api_key)
    batch_content = "\n---\n".join([f"ID: {tid}\nTEXTO: {text}" for tid, text in texts_with_ids])
    full_prompt = f"{prompt_text}\n\nProcesa estos asuntos parlamentarios:\n\n{batch_content}"
    
    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema={
                    "type": "OBJECT",
                    "properties": {
                        "resultados": {
                            "type": "ARRAY",
                            "items": {
                                "type": "OBJECT",
                                "properties": {
                                    "id": {"type": "STRING"},
                                    "titulo_ciudadano": {"type": "STRING"},
                                    "categoria_principal": {"type": "STRING"},
                                    "etiquetas": {"type": "ARRAY", "items": {"type": "STRING"}},
                                    "resumen_sencillo": {"type": "STRING"},
                                    "proponente": {"type": "STRING"}
                                },
                                "required": ["id", "titulo_ciudadano", "categoria_principal", "etiquetas", "resumen_sencillo"]
                            }
                        }
                    },
                    "required": ["resultados"]
                }
            ),
            contents=[full_prompt]
        )
        return _parse_response_json(response.text, texts_with_ids)
    except Exception as e:
        print(f"SDK AI Error: {e}", file=sys.stderr)
        return {tid: _fallback_categorization() for tid, _ in texts_with_ids}

def _categorize_batch_cli(texts_with_ids, prompt_text):
    print(f"  Usando gemini CLI (OAuth local) para {len(texts_with_ids)} textos...")
    batch_content = "\n---\n".join([f"ID: {tid}\nTEXTO: {text}" for tid, text in texts_with_ids])
    
    cli_instruction = "\nResponde EXCLUSIVAMENTE con el objeto JSON solicitado, empezando por { y terminando por }. No incluyas explicaciones ni bloques de código markdown."
    full_prompt = f"{prompt_text}\n\nProcesa estos asuntos parlamentarios y devuelve un objeto JSON con la clave 'resultados' que sea un array de objetos con: id, titulo_ciudadano, categoria_principal, etiquetas (array), resumen_sencillo, proponente:\n\n{batch_content}{cli_instruction}"
    
    try:
        # Simple call without extra flags that trigger "thinking"
        process = subprocess.Popen(
            ["gemini", "-y", "-m", "gemini-3-flash-preview", "-p", "Sigue las instrucciones enviadas por stdin para procesar los datos."],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate(input=full_prompt)
        
        if process.returncode != 0:
            print(f"CLI AI Error (Code {process.returncode}): {stderr}", file=sys.stderr)
            return {tid: _fallback_categorization() for tid, _ in texts_with_ids}
        
        if not stdout.strip():
            print(f"CLI AI Warning: Empty stdout. Stderr: {stderr}", file=sys.stderr)
            
        return _parse_response_json(stdout, texts_with_ids)
    except Exception as e:
        print(f"CLI Execution Error: {e}", file=sys.stderr)
        return {tid: _fallback_categorization() for tid, _ in texts_with_ids}

def _parse_response_json(raw_text, texts_with_ids):
    try:
        # Clean markdown if present
        clean_json = re.sub(r"```json\n?|\n?```", "", raw_text).strip()
        # Sometimes the CLI might output some ANSI or extra text, try to find the { ... }
        json_match = re.search(r'(\{.*\})', clean_json, re.DOTALL)
        if json_match:
            clean_json = json_match.group(1)
            
        data = json.loads(clean_json)
        result_map = {}
        for item in data.get("resultados", []):
            tid = item.pop("id")
            result_map[tid] = _validate_categorization(item)
            
        # Fill missing with fallbacks
        for tid, _ in texts_with_ids:
            if tid not in result_map:
                result_map[tid] = _fallback_categorization()
        return result_map
    except Exception as e:
        print(f"JSON Parsing Error: {e}", file=sys.stderr)
        return {tid: _fallback_categorization() for tid, _ in texts_with_ids}
