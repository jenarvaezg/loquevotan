# Checklist: Alta de una Nueva CCAA

Usa este checklist como runbook completo para integrar un nuevo ámbito autonómico en `Lo Que Votan`.

## 0) Preparación y diseño
- [ ] Definir `scope_id` (ej. `valencia`) y legislaturas objetivo.
- [ ] Auditar fuentes oficiales:
  - índice de sesiones/documentos,
  - detalle de diputados,
  - documentos de votación (PDF/HTML/TXT/API),
  - disponibilidad de foto/provincia.
- [ ] Definir formato de `id` de votación y `diputadoId` (estable y reproducible).

## 1) Estructura de carpetas y scripts
- [ ] Crear `scripts/<scope_id>/` con:
  - [ ] `scrape_sessions.py`
  - [ ] `scrape_diputados.py`
  - [ ] `download_*` (pdf/html/txt)
  - [ ] `parse_*` (extrae votos nominales)
  - [ ] `transform.py`
  - [ ] `run_update.py` (orquestación completa)
- [ ] Crear `data/<scope_id>/` y subcarpetas raw necesarias (`raw/pdf`, `raw/html`, `raw/txt`).
- [ ] Crear `public/data/<scope_id>/`.

## 2) Scraping de sesiones y diputados
- [ ] Guardar índice de sesiones en `data/<scope_id>/sessions_index.json` con `doc_id`, `legis_id`, `date`, `url`.
- [ ] Guardar diputados en `data/<scope_id>/diputados_raw.json` con:
  - `id`, `nombre`, `grupo`, `provincia`, `foto`, `nlegis`.
- [ ] Normalizar grupos (`PP`, `PSOE`, etc.) y resolver variantes de nombre.

## 3) Descarga y parsing de votaciones
- [ ] Descargar documentos faltantes sin redescargar históricos.
- [ ] Parsear votos nominales y generar `data/<scope_id>/votos_<LEG>_raw.json`.
- [ ] Mapear voto a `si | no | abstencion | no_vota`.
- [ ] Validar calidad del parser:
  - [ ] conteo de votaciones,
  - [ ] cobertura de diputados reconocidos,
  - [ ] grupos no mapeados (`Unknown`) bajo control.

## 4) IA y transformación a frontend
- [ ] Reusar `scripts/ai_utils.py` + `scripts/prompt_categorizacion.txt`.
- [ ] Mantener cache en `data/<scope_id>/cache_categorias.json`.
- [ ] Ejecutar transformación y generar:
  - [ ] `public/data/<scope_id>/votaciones_meta.json`
  - [ ] `public/data/<scope_id>/votos_<LEG>.json`
  - [ ] `public/data/<scope_id>/manifest_home.json`
- [ ] Incluir `dipFotos`, `dipProvincias`, `votIdById`, `groupAffinityByLeg`.

## 5) Integración en app
- [ ] Añadir ámbito en `public/data/ambitos.json` con legislaturas.
- [ ] Añadir bandera `public/assets/flags/<scope_id>.svg`.
- [ ] Actualizar `data/featured_votes.json` (opcional pero recomendado).
- [ ] Regenerar índice global: `python3 scripts/build_global_index.py`.

## 6) Quiz de alineación política
- [ ] Crear `public/data/<scope_id>/quiz.json` (básico).
- [ ] Crear `public/data/<scope_id>/quiz_advanced.json` (avanzado + `axis`).
- [ ] Verificar coherencia:
  - [ ] todos los `groups` existen y tienen voto en cada pregunta,
  - [ ] preguntas de desempate entre partidos similares,
  - [ ] temas electorales clave del territorio.

## 7) QA final (DoD)
- [ ] Ejecutar pipeline completo: `python3 scripts/<scope_id>/run_update.py`.
- [ ] Build: `npm run build`.
- [ ] E2E relevantes: `npx playwright test`.
- [ ] Revisión manual:
  - [ ] selector de ámbito y bandera,
  - [ ] home (`manifest_home`),
  - [ ] listados de diputados/votaciones,
  - [ ] detalle de votación y afinidad por grupos,
  - [ ] quiz básico/avanzado y compass.
- [ ] Documentar en PR: fuentes, supuestos, gaps de datos y pasos de regeneración.
