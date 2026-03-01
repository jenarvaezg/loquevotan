# Lo Que Votan - Roadmap & Backlog

## 🎯 OBJETIVO PRINCIPAL: Especial Elecciones CyL (Viralidad & Engagement)
*Foco: Atraer, retener y hacer que los usuarios compartan la app durante la campaña.*

### 1. Motor de Viralidad (Prioridad Absoluta)
- [x] **Quiz de Afinidad Cívica ("¿A quién voto en CyL?"):**
  - Seleccionar 10-15 votaciones clave y polarizantes de la última legislatura en CyL.
  - El usuario vota (A favor, En contra, Abstención) a ciegas.
  - Al final, la app calcula su % de afinidad real con cada partido/candidato en base al historial de voto.
- [x] **Encuesta / Analytics del Quiz:**
  - Integrar Google Analytics para guardar los resultados anonimizados.
- [ ] **Tarjetas Sociales Dinámicas (Open Graph):**
  - Generar imágenes OG para compartir en redes.
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

## Backlog (Largo plazo)

- [ ] **Otras CCAA:** Cataluña, País Vasco, C. Valenciana, etc.
- [ ] **Generación automática de Feeds RSS.**
- [ ] **Bookmarks/Favoritos locales.**
- [ ] **Datos históricos:** Legislaturas I-IX (1977-2011).
