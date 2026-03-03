# LoQueVotan - Roadmap operativo (pendiente)

Ultima revision: 2026-03-03 (enfoque PM).

Objetivo de este documento:
- priorizar lo que desbloquea fiabilidad, calidad de dato y crecimiento de producto;
- dejar cada bloque con criterio de exito verificable;
- evitar tareas ambiguas o desfasadas.

## Estado actual (contexto rapido)

- CI (`ci.yml`) en verde con `test:data`, unit y Playwright.
- Deploy a Cloudflare (`deploy.yml`) en verde tras CI de `main`.
- Worker con OG dinamico y API `/api/*` operativa (modo `d1+assets`).
- Sync D1 (`cloudflare-data-sync.yml`) operativo en ejecuciones manuales.
- Update semanal (`update-data.yml`) con cache local + fallback/upload de snapshots raw en R2 (operativo y validado).

## P0 - Operacion y datos (esta semana)

### 1) Cierre operativo de snapshot raw en R2 + run incremental real (cerrado)
Impacto:
- reducir duracion del update semanal y evitar re-descargas historicas innecesarias.

Tareas:
- [x] Lanzar `Update Voting Data` manual sobre el ultimo commit de `main` (`full_history=false`).
- [x] Verificar en logs que se cumple al menos una condicion:
- [x] `Restore raw data cache` con `cache-hit=true`, o
- [x] `Restore raw snapshot from R2` restaurando `raw-snapshots/main/latest.tar.gz`.
- [x] Verificar paso `Upload raw snapshot to R2 (if configured)` en verde.
- [x] Confirmar en R2 la existencia de:
- [x] `raw-snapshots/main/latest.tar.gz`
- [x] al menos un snapshot versionado `raw-snapshots/main/<timestamp>-<sha>.tar.gz`.

Evidencias:
- [x] Run `22622247625` (success): upload a `raw-snapshots/main/20260303T125159Z-e12fc8877308.tar.gz` y `raw-snapshots/main/latest.tar.gz`.
- [x] Run `22624881347` (success): subida a R2 en modo remoto confirmada (`Resource location: remote`).
- [x] Producción validada con backend `d1+assets` y `source: d1` en `/api/votaciones?scope=andalucia`.

DoD:
- [x] run incremental completado sin errores;
- [x] snapshot raw reutilizable confirmado en R2;
- [x] evidencias guardadas (run id + capturas/log snippets) en issue/PR de seguimiento.

Dependencias:
- secrets en GitHub: `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_R2_BUCKET_DATA_SNAPSHOTS`.

### 2) SLO del pipeline semanal (medible)
Impacto:
- previsibilidad operativa y deteccion de regresiones de rendimiento.

Tareas:
- [x] Definir objetivo de tiempo para run incremental:
- [x] `Update Voting Data` (sin full history): objetivo inicial <= 120 min.
- [x] `Cloudflare Data Sync` (scopes detectados): objetivo inicial <= 30 min.
- [ ] Guardar baseline real (3 ultimos lunes) en tabla de seguimiento.
- [x] Alertar si una ejecucion supera 1.5x baseline.

Estado:
- [x] Documento operativo creado: `docs/ops.md` (SLO, alertas y baseline provisional).
- [ ] Falta consolidar baseline con 3 lunes consecutivos.

DoD:
- [x] SLO documentado en este archivo o en `docs/ops.md`;
- [x] baseline inicial capturado;
- [x] criterio de alerta definido.

### 3) Calidad de datos Madrid (bloqueador de confianza)
Impacto:
- reduce casos de "asunto sin clasificar", mejora detalle de votos y consistencia en home/listados.

Tareas:
- [ ] Robustecer parsing nominal (menos heuristica de `group_votes`).
- [ ] Mejorar cobertura historica XII/XI/X (control de huecos y fallos de parseo por legislatura).
- [ ] Reducir titulos genericos con mejoras en transform + fallback.
- [ ] Crear reporte QA por run con:
- [ ] % titulos genericos,
- [ ] % votos sin asignacion nominal,
- [ ] grupos `Unknown`.

DoD:
- [ ] titulos genericos en Madrid < 2%;
- [ ] `Unknown` en Madrid < 1% del total de votos de grupo;
- [ ] reporte QA publicado en artefacto CI.

## P1 - Producto y trazabilidad (siguiente bloque)

### 4) Full-pass IA de Andalucia para titulos residuales
Impacto:
- mejora legibilidad del contenido compartido y de home.

Tareas:
- [ ] Ejecutar pasada IA completa en Andalucia con cache de categorias.
- [ ] Listar outliers (titulos muy cortos, genericos, o duplicados).
- [ ] Corregir prompt/fallback para evitar recaidas en siguientes runs.

DoD:
- [ ] no quedan titulos "Asunto parlamentario sin clasificar" en muestras recientes;
- [ ] mejora validada en `manifest_home.json` y detalle de votacion.

### 5) Filtro por rango de fecha en `/votaciones`
Impacto:
- usabilidad directa para analisis temporal y enlaces compartibles.

Tareas:
- [ ] Añadir controles `from/to` en UI.
- [ ] Soportar query params persistentes en URL.
- [ ] Integrar con API Worker (`from`, `to`) y fallback local.
- [ ] Cobertura de tests UI + API.

DoD:
- [ ] filtro funcional en nacional + CCAA;
- [ ] enlaces con rango reproducen exactamente el listado.

### 6) Cobertura de tests en share/OG y Worker API
Impacto:
- evita regresiones silenciosas en rutas mas visibles de difusion.

Tareas:
- [ ] Tests E2E para `/share/votacion/...` y `/share/diputado/...` (metatags y redireccion final).
- [ ] Tests de contrato API para `/api/votacion/:scope/:id` y `/api/diputado/:scope/:name`.
- [ ] Test de smoke para OG imagen (`/og/*`) con `200` + `content-type` esperado.

DoD:
- [ ] suite ejecuta en CI y falla ante ruptura de contrato/meta OG.

### 7) Trazabilidad completa por votacion (`source_hash`)
Impacto:
- transparencia publica y debugging de discrepancias.

Tareas:
- [ ] Añadir `source_hash` y `source_url`/`source_ref` en transform.
- [ ] Exponer trazabilidad en API (`/api/votacion`).
- [ ] Mostrar referencia en UI de detalle (con etiqueta "fuente oficial").

DoD:
- [ ] cualquier votacion permite rastrear su origen y version de contenido.

### 8) Tránsfugas y cambios de grupo
Impacto:
- mejora lectura politica de series largas y casos individuales.

Tareas:
- [ ] Definir regla de deteccion (cambio de grupo por legislatura/fecha).
- [ ] Guardar historial de grupo por diputado.
- [ ] Mostrar evento de cambio en perfil y en metrica agregada.

DoD:
- [ ] casos detectados automaticamente sin hardcode manual;
- [ ] visualizacion clara en ficha de diputado.

## P2 - Escalado y valor ciudadano

### 9) Rendimiento en listados grandes
- [ ] Virtualizacion/paginacion avanzada.
- [ ] Presupuesto de rendimiento (LCP/INP) y medicion recurrente.
- [ ] Objetivo: evitar degradacion visible en ambitos de mayor volumen.

### 10) Metodologia publica ampliada
- [ ] Separar "coincidencia tactica" vs "alineamiento ideologico".
- [ ] Publicar ficha metodologica completa (afinidad + compass + limites/sesgos).
- [ ] Versionado de cambios metodologicos.

### 11) Curacion continua del quiz
- [ ] Mejorar banco de preguntas para desempates reales.
- [ ] Cobertura de temas clave por territorio.
- [ ] Auditoria de sesgos por bloque ideologico.

### 12) Features de seguimiento ciudadano
- [ ] Alertas de cambio de postura por partido y legislatura.
- [ ] Watchlist (diputados/temas) y notificaciones.
- [ ] RSS de cambios/votaciones destacadas.

## Calidad y confianza publica

### 13) Changelog de datos y metodologia
- [ ] Publicar changelog por version (fuentes, parser, reglas, impacto).
- [ ] Mantener historial accesible desde la web.

### 14) Diff publico entre actualizaciones
- [ ] Exponer diff de cada update en endpoint/pagina publica.
- [ ] Reusar el resumen de CI como base, pero visible para usuarios.

## Backlog largo plazo

- [ ] Nuevas CCAA: Cataluna, Pais Vasco, C. Valenciana, etc.
- [ ] Históricos I-IX (1977-2011).
- [ ] Favoritos locales de votaciones/diputados.

## Regla de mantenimiento de este TODO

En cada PR relevante:
- [ ] mover tareas hechas a changelog/PR y borrarlas de aqui;
- [ ] convertir tareas ambiguas en tareas con DoD;
- [ ] no dejar items "abiertos" sin responsable o sin siguiente accion concreta.
