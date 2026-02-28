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

## Backlog (Largo plazo)

- [ ] **Otras CCAA:** Cataluña, País Vasco, C. Valenciana, etc.
- [ ] **Generación automática de Feeds RSS.**
- [ ] **Bookmarks/Favoritos locales.**
- [ ] **Datos históricos:** Legislaturas I-IX (1977-2011).
