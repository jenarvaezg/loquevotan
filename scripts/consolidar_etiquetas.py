#!/usr/bin/env python3
"""
Analiza las 3830 etiquetas existentes y propone un vocabulario canonico
de ~80-100 etiquetas, agrupando las existentes por similitud semantica.

Paso 1: Genera el vocabulario (este script)
Paso 2: Se revisa manualmente
Paso 3: Se actualiza el prompt de Gemini para usar solo estas etiquetas
Paso 4: Se recategoriza todo
"""

import json
import re
from collections import Counter, defaultdict

CACHE_FILE = "data/cache_categorias.json"


def load_tags():
    with open(CACHE_FILE, encoding="utf-8") as f:
        cache = json.load(f)

    tag_counts = Counter()
    cat_tags = defaultdict(Counter)  # categoria -> tag -> count

    for entry in cache.values():
        cat = entry.get("categoria_principal", "Otros")
        for tag in entry.get("etiquetas", []):
            tag_counts[tag] += 1
            cat_tags[cat][tag] += 1

    return tag_counts, cat_tags


def cluster_tags(tag_counts):
    """Group tags by semantic similarity using word overlap."""

    # Normalize: split on _ and create a "topic signature"
    clusters = defaultdict(list)  # canonical -> [(tag, count)]

    # Define canonical topics by key nouns
    # Order matters: more specific patterns FIRST to avoid greedy matches
    TOPIC_KEYWORDS = {
        # ── Economia ──
        "presupuestos": ["presupuesto", "presupuestos", "presupuestario", "presupuestaria",
                         "cuentas_estado", "contingencia", "fondo_reserva", "credito_extraordinario",
                         "seccion_presupuest", "reequilibrio", "financiar_estado"],
        "impuestos": ["impuesto", "impuestos", "fiscal", "tributario", "tributaria", "iva", "irpf",
                      "imposicion", "recaudacion", "tipo_impositivo"],
        "deuda_publica": ["deuda"],
        "gasto_publico": ["gasto", "morosidad_publica"],
        "deficit": ["deficit"],
        "fraude_fiscal": ["fraude", "evasion", "antifraude", "paraisos_fiscales"],
        "emprendimiento": ["emprendedor", "pyme", "autonomo"],
        "consumidores": ["consumidor", "consumidores", "consumo", "atencion_cliente",
                         "ahorrador", "ahorradores", "precio", "precios"],
        "sector_financiero": ["bancario", "bancaria", "banco", "financiero", "financiera"],
        "economia": ["economico", "economica", "crecimiento_economico", "anticrisis",
                     "crisis_economica", "recesion", "pib", "inflacion", "adquisitivo",
                     "comercio_exterior"],
        "turismo": ["turismo", "turistic", "turistico"],

        # ── Trabajo ──
        "empleo": ["empleo", "desempleo", "desempleado", "desempleados", "paro",
                   "parado", "parados"],
        "condiciones_laborales": ["laboral", "laborales", "salarial", "salario", "salarios", "sueldo",
                                  "trabajador", "trabajadores", "precariedad", "estiba",
                                  "emplead", "subcontrat", "convenio_colectivo"],
        "pensiones": ["pension", "pensiones", "jubilacion", "pacto_toledo", "jubilado", "jubilados"],
        "jornada_laboral": ["jornada"],
        "conciliacion": ["conciliacion", "conciliar", "maternidad", "paternidad",
                         "permiso_parental", "corresponsabilidad", "natalidad",
                         "permiso_nacimiento", "permisos_nacimiento"],
        "seguridad_social": ["seguridad_social"],

        # ── Sanidad ──
        "sanidad_publica": ["sanidad", "sanitario", "sanitaria", "sanitarios",
                            "hospital", "atencion_primaria", "farmac", "medicament",
                            "copago", "paliativ", "donante", "organo", "agencia_salud"],
        "salud_mental": ["mental", "psicolog", "suicidio"],
        "eutanasia": ["eutanasia", "muerte_digna"],
        "enfermedades": ["enferm", "ela", "cancer", "rara", "cronic", "vacuna", "pandemia", "covid"],
        "drogas": ["drogas", "cannabis", "adiccion", "estupefaciente"],

        # ── Educacion ──
        "educacion": ["educacion", "educativo", "educativa", "educativas", "educativos",
                      "escolar", "escuela"],
        "universidad": ["universidad", "universitari", "tasas_universitarias"],
        "becas": ["beca"],
        "formacion_profesional": ["formacion_profesional", "fp_dual"],
        "ciencia": ["ciencia", "cientifico", "cientifica", "investigacion_cientifica",
                    "i+d", "investigador"],

        # ── Vivienda ──
        "vivienda": ["vivienda", "alquiler", "hipoteca", "desahucio", "desahucios",
                     "inquilino", "dacion_en_pago", "arrendamiento"],
        "okupacion": ["okupa", "okupacion"],

        # ── Derechos sociales ──
        "igualdad_genero": ["genero", "machista", "machismo", "feminismo", "paridad",
                            "proteger_mujeres", "mujer", "mujeres", "brecha_salarial"],
        "violencia_genero": ["violencia_genero", "violencia_machista"],
        "discapacidad": ["discapacidad", "dependencia", "dependientes"],
        "infancia": ["infancia", "menores", "menor"],
        "familias": ["familia", "familias", "familiar"],
        "pobreza": ["pobreza", "exclusion", "vulnerabl", "ayudas_sociales",
                    "bienestar", "recortes_sociales", "servicios_publicos",
                    "ingreso_minimo", "renta_minima"],
        "derechos_lgbti": ["lgbti", "lgtbi", "transexual", "homosexual"],
        "inmigracion": ["inmigra", "migra", "extranjeria", "refugiad", "asilo",
                        "nacionalidad"],
        "libertades_civiles": ["libertad", "privacidad", "proteccion_datos",
                               "datos_personales", "mordaza", "derechos_fundamentales",
                               "odio", "discriminacion", "minoria"],
        "derechos_animales": ["animal", "animales", "maltrato_animal", "tauromaquia", "toros"],
        "tercera_edad": ["tercera_edad", "geriatr"],

        # ── Justicia ──
        "codigo_penal": ["penal", "penas", "delito", "codigo_civil", "reinciden"],
        "poder_judicial": ["judicial", "jueces", "juez", "magistrad", "justicia",
                           "juzgado", "juzgados", "fiscalia", "fiscal_general", "cgpj"],
        "tribunal_constitucional": ["constitucional", "constitucion"],
        "corrupcion": ["corrupcion"],
        "memoria_historica": ["memoria_historica", "memoria_democr", "franquismo", "fosas"],

        # ── Interior ──
        "seguridad_ciudadana": ["seguridad_ciudadana", "policia", "policial",
                                "guardia_civil", "guardia_urbana", "delincuencia",
                                "seguridad_nacional"],
        "terrorismo": ["terrorismo", "terrorista", "eta"],
        "trafico": ["trafico", "vial", "dgt"],
        "proteccion_civil": ["emergencia", "catastrofe", "dana", "incendio",
                             "seismo", "inundacion", "reconstruccion", "reconstruir",
                             "zonas_afectadas", "bombero", "forestal"],
        "narcotrafico": ["narcotrafico", "narcotrafic"],

        # ── Medio ambiente ──
        "cambio_climatico": ["climatico", "emisiones", "carbono", "calentamiento"],
        "energia": ["energia", "energetico", "energetica", "electrico", "electricidad",
                    "renovable", "nuclear", "apagon", "suministro_electrico",
                    "pobreza_energetica", "tarifa_electrica"],
        "agua": ["hidric", "agua", "sequia", "riego", "trasvase"],
        "biodiversidad": ["biodiversidad", "fauna", "flora", "natural", "parque_nacional"],
        "residuos": ["residuo", "desperdicio", "reciclaje", "plastico"],
        "costas": ["costa", "litoral", "maritim", "playa"],
        "medio_ambiente": ["medio_ambiente", "contaminacion", "ambiental", "sostenib", "ecolog"],

        # ── Infraestructuras ──
        "ferrocarril": ["ferroviari", "tren", "trenes", "renfe", "cercanias", "ave",
                        "alta_velocidad", "corredor_mediterraneo"],
        "carreteras": ["carretera", "autopista", "peaje", "autovia"],
        "transporte_publico": ["transporte"],
        "telecomunicaciones": ["telecomunicacion", "digital", "internet",
                               "ciberseguridad", "tecnolog", "inteligencia_artificial"],
        "obras_publicas": ["obra_publica", "infraestructura"],
        "movilidad": ["movilidad"],

        # ── Politica territorial ──
        "financiacion_autonomica": ["autonomic", "autogobierno", "autonomia"],
        "financiacion_local": ["ayuntamiento", "municipio", "municipal", "diputacion",
                               "entidades_locales", "administracion_local"],
        "despoblacion": ["despoblacion", "rural", "vacio"],
        "cataluna": ["catalan", "catalun"],
        "pais_vasco": ["vasco", "euskadi", "navarra"],

        # ── Asuntos exteriores ──
        "acuerdos_internacionales": ["internacional", "tratado", "convenio", "comercial"],
        "union_europea": ["europa", "europeo", "europea", "comunitari", "fondos_europeos"],
        "derechos_humanos": ["humanos"],
        "cooperacion": ["cooperacion"],
        "defensa": ["defensa", "militar", "ejercito", "otan", "armamento",
                    "informacion_clasificada", "secretos_oficiales"],
        "palestina_israel": ["palestin", "israel", "gaza"],
        "venezuela": ["venezuela", "maduro"],
        "marruecos": ["marruecos", "sahara", "ceuta", "melilla"],

        # ── Gobernanza ──
        "procedimiento_parlamentario": ["parlamentario", "reglamento_congreso", "tramite", "tramitacion",
                                        "pleno", "articulado", "tramitar_ley", "tramitar_urgencia",
                                        "proyecto_ley", "proposicion_ley", "enmienda", "devolver",
                                        "convalidar", "convalidacion", "decreto_ley", "articulos_ley",
                                        "urgencia", "titulo_ley", "disposicion", "reglamento",
                                        "comision", "subcomision", "ponencia",
                                        "rechazar_ley", "aprobar_ley", "votar_ley",
                                        "lectura_unica", "dictamen", "texto_alternativo",
                                        "interes_publico"],
        "control_gobierno": ["responsabilidades_gobierno", "responsabilidades_politicas",
                             "controlar_gobierno", "explicaciones_gobierno", "reprobar",
                             "dimision", "cese", "destituir", "responsabilidades_ministro",
                             "accion_gobierno", "explicaciones", "depurar_responsabilid",
                             "responsabilidades"],
        "transparencia": ["transparencia", "lobby", "lobbies", "grupos_interes",
                          "incompatibilid", "declaracion_actividades",
                          "contratacion_publica"],
        "ley_electoral": ["electoral"],
        "mocion": ["mocion", "censura", "confianza"],
        "comision_investigacion": ["comision_investigacion", "investigar"],
        "monarquia": ["monarquia", "corona", "rey", "casa_real"],
        "administracion_publica": ["funcion_publica", "funcionario", "administracion_publica",
                                   "oposicion", "servicio_publico", "servicios_publicos",
                                   "sector_publico"],

        # ── Agricultura ──
        "agricultura": ["agrar", "agricol", "ganad", "pesquer", "sector_primario",
                        "pac", "agricultor", "pesca"],
        "alimentacion": ["alimentar", "alimentacion", "alimentaria", "comida", "alimento"],

        # ── Cultura ──
        "cultura": ["cultura", "cultural", "patrimonio", "museo", "deporte", "deportiv",
                    "propiedad_intelectual", "artistico", "artisticas"],
        "medios_comunicacion": ["prensa", "medios_comunicacion", "periodis",
                                "audiovisual", "rtve"],
        "lenguas": ["lengua", "linguist", "idioma", "castellano"],
    }

    tagged = set()
    for canonical, keywords in TOPIC_KEYWORDS.items():
        for tag, count in tag_counts.items():
            if tag in tagged:
                continue
            tag_lower = tag.lower()
            for kw in keywords:
                if kw in tag_lower:
                    clusters[canonical].append((tag, count))
                    tagged.add(tag)
                    break

    # Remaining unclustered
    unclustered = [(tag, count) for tag, count in tag_counts.items() if tag not in tagged]

    return clusters, unclustered


def main():
    tag_counts, cat_tags = load_tags()

    print(f"Total etiquetas unicas: {len(tag_counts)}")
    print(f"Total usos: {sum(tag_counts.values())}")
    print()

    clusters, unclustered = cluster_tags(tag_counts)

    # Sort clusters by total usage
    cluster_totals = {}
    for canonical, tags in clusters.items():
        cluster_totals[canonical] = sum(c for _, c in tags)

    print("=" * 70)
    print("VOCABULARIO CANONICO PROPUESTO")
    print("=" * 70)

    total_covered = 0
    for canonical, total in sorted(cluster_totals.items(), key=lambda x: -x[1]):
        tags = clusters[canonical]
        total_covered += total
        unique = len(tags)
        examples = sorted(tags, key=lambda x: -x[1])[:5]
        examples_str = ", ".join(f"{t}({c})" for t, c in examples)
        print(f"\n  {canonical}  [{total} usos, {unique} variantes]")
        print(f"    Ej: {examples_str}")

    print()
    print("=" * 70)

    unclustered_total = sum(c for _, c in unclustered)
    total_all = sum(tag_counts.values())

    print(f"\nCOBERTURA:")
    print(f"  Etiquetas canonicas: {len(clusters)}")
    print(f"  Tags cubiertos: {total_covered}/{total_all} ({total_covered/total_all*100:.1f}%)")
    print(f"  Tags sin agrupar: {len(unclustered)} ({unclustered_total} usos)")
    print()

    # Show top unclustered
    unclustered_sorted = sorted(unclustered, key=lambda x: -x[1])[:50]
    print("Top 50 sin agrupar:")
    for t, c in unclustered_sorted:
        print(f"  {t}: {c}")

    # Final clean list for prompt
    print()
    print("=" * 70)
    print("LISTADO FINAL (para prompt de Gemini):")
    print("=" * 70)
    for canonical in sorted(clusters.keys()):
        total = cluster_totals[canonical]
        print(f"  {canonical} ({total})")
    print(f"\nTotal: {len(clusters)} etiquetas canonicas")


if __name__ == "__main__":
    main()
