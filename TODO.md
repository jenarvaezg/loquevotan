# Lo Que Votan - Roadmap & Backlog

## 🎯 OBJETIVO PRINCIPAL: Especial Elecciones CyL (Viralidad & Engagement)
*Foco: Atraer, retener y hacer que los usuarios compartan la app durante la campaña.*

### 1. Motor de Viralidad (Prioridad Absoluta)
- [x] **Quiz de Afinidad Cívica ("¿A quién voto en CyL?"):**
  - Seleccionar 10-15 votaciones clave y polarizantes de la última legislatura en CyL.
  - El usuario vota (A favor, En contra, Abstención) a ciegas.
  - Al final, la app calcula su % de afinidad real con cada partido/candidato en base al historial de voto.
  - *Metodología:* Explicar de forma transparente (y enlazando a las votaciones originales) por qué sale ese resultado. Contrastar el sentido de voto real de la legislatura anterior con las promesas de los programas electorales actuales.
- [x] **Encuesta / Analytics del Quiz:**
  - Integrar Google Analytics (o PostHog/Plausible para mayor privacidad) configurando eventos personalizados para guardar los resultados *anonimizados* del Quiz.
  - Esto permitirá generar artículos/hilos tipo "El 60% de los votantes del Quiz en León prefiere las políticas de X partido, pero no lo saben".
- [ ] **Tarjetas Sociales Dinámicas (Open Graph):**
  - Generar imágenes OG para que al pasar un link de un político o del resultado del Quiz por WhatsApp/Twitter salga su foto, sus stats o el % de afinidad del usuario. (Requiere Edge API o generación estática).
- [x] **Botón "Fiscalizar" / Share Accountability:**
  - En la ficha temática de un diputado, añadir un botón para exportar esa "tarjeta" como imagen (usando `html2canvas`) para subir directa a Instagram Stories o Twitter.
- [x] **Buscador de representantes por Provincia:**
  - Vital para CyL. Permitir filtrar la vista de Diputados por su circunscripción (ej. León, Valladolid...) para que el usuario encuentre a "su" candidato local.

---

## Completado

- [x] **Arquitectura y Scraping Base:** Scraping Legislaturas X-XV completado. Arquitectura de JSON optimizada (3-tier).
- [x] **Andalucía:** Integración completa (Scraping PDFs, extracción de votos, extracción de fotos, transformación a JSON).
- [x] **Castilla y León:** Integración completa (Parsing de Diarios de Sesiones TXT para votos nominales).
- [x] **Madrid:** Integración básica (Diputados XIII y votación de Investidura 2023).
- [x] **Optimización de Repo:** Configuración de .gitignore y limpieza de archivos "raw" (~200MB eliminados).
- [x] **UI/UX Global:** Buscador global, selector de ámbito (banderas), compatibilidad con Dark Mode, mejoras de contraste WCAG.
- [x] **Taxonomía Unificada:** Cerebro de IA (`ai_utils.py`) compartido entre todas las instituciones.

---

## Fase 2: Calidad de Datos e Inteligencia (Pendiente)

- [ ] **AI Full-Pass para CCAA:**
  - Procesar los ~400 temas de Andalucía XII y los ~120 temas de CyL XI con IA para eliminar títulos crípticos del BOPA/Diarios.
  - *Estado:* Pendiente por errores de cuota/configuración en el CLI de Gemini. 
- [/] **Detalle de "Rebeldía" y Tránsfugas:** (Ranking listo, falta detalle en perfil) Mostrar exactamente en qué votaciones un diputado rompió la disciplina de su grupo parlamentario.
- [x] **Ranking de Asistencia ("Los que menos van"):** Destacar el porcentaje de absentismo ("No Vota") de cada diputado en una vista dedicada de ránkings.
- [ ] **Soporte para Widgets/Embeds (`<iframe>`):** Permitir a la prensa incrustar gráficos de votaciones.

---

## Fase 3: Deuda Técnica y Robustez

- [ ] **Filtros Combinados / Buscador Avanzado:** Permitir buscar combinando (Etiqueta + Rango de Fechas + Proponente + Resultado).
- [ ] **Migrar CSS Monolítico:** Pasar el resto de `custom.css` a estilos `scoped`.
- [ ] **Tests E2E y Unitarios:** Cobertura de flujos críticos multi-parlamento.

---

## Backlog (Largo plazo)

- [ ] **Otras CCAA:** Investigar Cataluña (parlament.cat), País Vasco (legebiltzarra.eus), Comunidad Valenciana, etc.
- [ ] **Generación automática de Feeds RSS:** Seguimiento externo.
- [ ] **Bookmarks/Favoritos locales:** `localStorage`.
- [ ] **Datos históricos:** Legislaturas I-IX del Congreso (1977-2011).
