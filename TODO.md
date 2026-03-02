# Lo Que Votan - Roadmap & Backlog

## 🎯 OBJETIVO PRINCIPAL: Especial Elecciones CyL (Viralidad & Engagement)
*Foco: Atraer, retener y hacer que los usuarios compartan la app durante la campaña.*

## Priorización Ejecutiva (Pendientes)
*Esta priorización reordena tareas ya listadas abajo.*

### P0 (hacer ahora)
1. **Pipeline CI de datos** (`test:data-integrity` + checks de estructura/tamaño en PR).
2. **Homogeneizar `run_update.py` con fail-fast** (evitar publicar datasets parciales).
3. **Fecha de actualización por ámbito visible** (transparencia operativa inmediata).
4. **Diff automático entre actualizaciones** (QA rápido y trazable).
5. **Tarjetas sociales dinámicas (OG)** (base implementada con Cloudflare Workers en rutas `/share/...`).
6. **Soporte widgets/embeds** (distribución en medios locales y terceros).

### P1 (siguiente bloque)
1. **Madrid datos**: bypass scraping + histórico XII/XI/X + AI pass de títulos.
2. **AI Full-Pass Andalucía** (limpieza de títulos crípticos de BOPA).
3. **Filtros combinados / buscador avanzado** (etiqueta + fecha + proponente).
4. **Cobertura de tests E2E/unitarios** en flujos críticos.
5. **Trazabilidad por votación** (`source_url` + `source_hash`).
6. **Accesibilidad automatizada en CI** (`axe` en vistas clave).
7. **Detalle de rebeldía/tránsfugas** completo en perfil de diputado.
8. **Glosario institucional contextual** (dictamen, voto particular, transaccional, etc.).

### P2 (después)
1. **Rendimiento de listados grandes** (virtualización + presupuesto LCP/INP).
2. **Changelog público de metodología y datos** por release.
3. **Separar coincidencia táctica vs alineamiento ideológico** en explicaciones públicas.
4. **Ficha metodológica pública completa** (afinidad + compass).
5. **Alertas de cambio de postura por partido** entre legislaturas.
6. **Watchlist ciudadana** (diputados/temas).
7. **Migrar CSS monolítico** a `scoped`.
8. **Backlog largo plazo**: otras CCAA, RSS, favoritos, histórico I-IX.

### 1. Motor de Viralidad (Prioridad Absoluta)
- [x] **Quiz de Afinidad Cívica ("¿A quién voto en CyL?"):**
  - Seleccionar 10-15 votaciones clave y polarizantes de la última legislatura en CyL.
  - El usuario vota (A favor, En contra, Abstención) a ciegas.
  - Al final, la app calcula su % de afinidad real con cada partido/candidato en base al historial de voto.
- [x] **Encuesta / Analytics del Quiz:**
  - Integrar Google Analytics para guardar los resultados anonimizados.
- [x] **Tarjetas Sociales Dinámicas (Open Graph):**
  - OG dinámico server-side con Cloudflare Worker para rutas:
    - `/share/votacion/:scope/:id`
    - `/share/diputado/:scope/:name`
  - `ShareBar` usa estas URLs para que redes lean metadatos antes de redirigir a la SPA.
  - Pendiente opcional: generación de imagen OG personalizada por recurso (ahora usa `og-image.png`).
- [x] **Botón "Fiscalizar" / Share Accountability:**
  - Exportar ficha de diputado como imagen.
- [x] **Buscador de representantes por Provincia:**
  - Filtrar por circunscripción local.

---

## Completado

- [x] **Arquitectura y Scraping Base:** Legislaturas X-XV.
- [x] **Andalucía:** Integración completa del histórico (2012-2026).
- [x] **Castilla y León:** Integración completa (Votos nominales + Títulos ciudadanos e IA al 100%).
- [x] **Madrid:** Integración básica (Diputados XIII, Investidura 2023 y leyes recientes).
- [x] **Optimización de Repo:** Configuración de .gitignore y limpieza de archivos "raw" (~200MB eliminados).
- [x] **UI/UX Global:** Buscador, selector de ámbito, Dark Mode, contraste WCAG.
- [x] **Taxonomía Unificada:** Cerebro de IA (`ai_utils.py`) compartido.
- [x] **Global Index:** Unificación de 1.927 diputados en índice global.

---

## Fase 2: Calidad de Datos e Inteligencia (Pendiente)

### 🏙️ Específico Madrid
- [ ] **Bypass Permanente / Scraping Avanzado:** Investigar fuentes más robustas para votos nominales.
- [ ] **Histórico Madrid:** Descargar y procesar Legislaturas XII, XI y X (vía servidor estático).
- [ ] **AI Pass Madrid:** Generar títulos ciudadanos para todas las votaciones.

### 🧠 Inteligencia y Funcionalidad Global
- [ ] **AI Full-Pass Andalucía:**
  - Procesar los ~400 temas de Andalucía XII con IA para eliminar títulos crípticos del BOPA.
  - *Estado:* Pendiente por errores de cuota/configuración en el CLI de Gemini. 
- [/] **Detalle de "Rebeldía" y Tránsfugas:** (Ranking listo, falta detalle en perfil) Mostrar votos específicos.
- [x] **Ranking de Asistencia ("Los que menos van"):** Vista dedicada de ránkings.
- [ ] **Soporte para Widgets/Embeds:** Para prensa local.

---

## Fase 3: Deuda Técnica y Robustez

- [ ] **Filtros Combinados / Buscador Avanzado:** (Etiqueta + Fecha + Proponente).
- [ ] **Migrar CSS Monolítico:** Estilos `scoped`.
- [ ] **Tests E2E y Unitarios:** Cobertura de flujos críticos.

---

## Fase 3.1: Puntos de Ataque Detectados (Auditoría técnica + UX/UI + politología)

### 🚨 Críticos (producto y fiabilidad)
- [x] **Fallback de votación no encontrada:** En `VotacionDetail`, mostrar estado 404/empty en vez de pantalla en blanco cuando el ID no existe.
- [x] **Error-state real en Home:** Si falla `manifest_home.json`, mostrar mensaje + botón de reintento (evitar spinner infinito).
- [x] **Estabilizar suite E2E rota (3 tests):**
  - [x] Reemplazar selectores frágiles (`select.nth(2)`) por `data-testid`.
  - [x] Alinear tests de Home/Navigation con el layout actual (ya no existe bloque “rebels” en Home).
  - [x] Añadir checks de contrato mínimo por vista para evitar regresiones silenciosas.

### ⚙️ Técnicos (rendimiento y mantenibilidad)
- [x] **Optimizar computeds pesados:** Evitar `Set/Map` recreados dentro de bucles en vistas con históricos grandes (`Votaciones`, `DiputadoDetail`).
- [ ] **Homogeneizar pipelines `run_update.py`:** Política fail-fast consistente (Andalucía/CyL/Madrid) para no publicar datasets parciales.
- [x] **Resiliencia de carga por ámbito:** añadir timeout + retry con backoff y telemetría de error por `scope`.
- [x] **Cobertura de tests de datos:** tests de integridad de `votaciones_meta.json`, `votIdById`, y `groupAffinityByLeg`.

### 🎨 UX/UI (claridad para usuario de a pie)
- [x] **Revisar copy prescriptivo del Quiz:** cambiar “¿A quién deberías votar?” por wording menos normativo (“¿Con quién coincide más tu voto?”).
- [ ] **Glosario contextual institucional:** microayudas para términos como “dictamen”, “voto particular”, “transaccional”, “deducción grupal”.
- [x] **Consistencia de fuentes en footer:** reflejar explícitamente que hay datos de Congreso + Parlamentos autonómicos (no solo Congreso).
- [x] **Estados vacíos/error unificados:** patrón visual y textual común en Home, Votación, Grupo, Afinidad, Comparador y 404 (quiz pendiente aparte).

### 🧭 Metodología política (rigor)
- [ ] **Ficha metodológica pública (afinidad + compass):** supuestos, límites, sesgos y casos donde el modelo no discrimina bien.
- [x] **Incertidumbre explícita del compass:** mostrar intervalo o banda de confianza por eje, no solo porcentaje global.
- [ ] **Curación del banco de preguntas del quiz:** reducir preguntas de alto consenso transversal y subir peso a preguntas realmente discriminantes.
- [ ] **Separar “coincidencia táctica” de “alineamiento ideológico”:** explicar cuándo una coincidencia de voto no implica cercanía doctrinal.

---

## Fase 3.2: Mejoras de Alto Impacto (operación + confianza pública)

- [ ] **Fecha de actualización por ámbito visible:** mostrar “última actualización” y avisar cuando un ámbito esté desfasado.
- [ ] **Diff automático entre actualizaciones de datos:** resumen de cambios (votaciones nuevas, diputados nuevos, recategorizaciones) para QA y transparencia.
- [ ] **Trazabilidad por votación (fuente + hash):** persistir y exponer `source_url` + `source_hash` para auditoría reproducible.
- [ ] **Pipeline CI de datos:** ejecutar `npm run test:data-integrity` + checks de estructura/tamaño en cada PR.
- [ ] **Rendimiento en listados grandes:** virtualización de tablas/listas y presupuesto de rendimiento (LCP/INP) con alertas.
- [ ] **Accesibilidad automatizada en CI:** incorporar tests `axe` en vistas clave (home, votación, diputado, grupos).
- [ ] **Alertas de cambio de postura por partido:** detectar y mostrar cambios de posición por tema entre legislaturas.
- [ ] **Watchlist ciudadana (diputados/temas):** seguimiento de entidades con vista de novedades.
- [ ] **Changelog público de metodología y datos:** versionado por release para explicar cambios y reforzar confianza.

---

## Backlog (Largo plazo)

- [ ] **Otras CCAA:** Cataluña, País Vasco, C. Valenciana, etc.
- [ ] **Generación automática de Feeds RSS.**
- [ ] **Bookmarks/Favoritos locales.**
- [ ] **Datos históricos:** Legislaturas I-IX (1977-2011).
