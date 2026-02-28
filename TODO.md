# Lo Que Votan - Roadmap & Backlog

## 🎯 OBJETIVO PRINCIPAL: Especial Elecciones CyL (Viralidad & Engagement)
*Foco: Atraer, retener y hacer que los usuarios compartan la app durante la campaña.*

### 1. Motor de Viralidad (Prioridad Absoluta)
- [ ] **Quiz de Afinidad Cívica ("¿A quién voto en CyL?"):**
  - Seleccionar 10-15 votaciones clave y polarizantes de la última legislatura en CyL.
  - El usuario vota (A favor, En contra, Abstención) a ciegas.
  - Al final, la app calcula su % de afinidad real con cada partido/candidato en base al historial de voto.
  - *Metodología:* Explicar de forma transparente (y enlazando a las votaciones originales) por qué sale ese resultado. Contrastar el sentido de voto real de la legislatura anterior con las promesas de los programas electorales actuales.
- [ ] **Encuesta / Analytics del Quiz:**
  - Integrar Google Analytics (o PostHog/Plausible para mayor privacidad) configurando eventos personalizados para guardar los resultados *anonimizados* del Quiz.
  - Esto permitirá generar artículos/hilos tipo "El 60% de los votantes del Quiz en León prefiere las políticas de X partido, pero no lo saben".
- [ ] **Tarjetas Sociales Dinámicas (Open Graph):**
  - Generar imágenes OG para que al pasar un link de un político o del resultado del Quiz por WhatsApp/Twitter salga su foto, sus stats o el % de afinidad del usuario. (Requiere Edge API o generación estática).
- [ ] **Botón "Fiscalizar" / Share Accountability:**
  - En la ficha temática de un diputado, añadir un botón para exportar esa "tarjeta" como imagen (usando `html2canvas`) para subir directa a Instagram Stories o Twitter.
- [ ] **Buscador de representantes por Provincia:**
  - Vital para CyL. Permitir filtrar la vista de Diputados por su circunscripción (ej. León, Valladolid...) para que el usuario encuentre a "su" candidato local.

---

## Completado

- [x] **Arquitectura y Scraping Base:** Scraping Legislaturas X-XV completado. Arquitectura de JSON optimizada (3-tier).
- [x] **Datos Autonómicos:** Integración completa de las Cortes de Andalucía (Scraping PDFs, extracción de votos, extracción de fotos, transformación a JSON alineado con el nacional).
- [x] **UI/UX Global:** Buscador global, badges clicables, reordenación de tablas en móvil, compatibilidad con Dark Mode, mejoras de contraste WCAG, y fuentes corporativas (Source Sans 3 + DM Serif Display).
- [x] **Arquitectura de Información Multi-Cámara:** Selector superior rediseñado con banderas vectoriales (SVG). Trazabilidad de políticos entre distintas cámaras (ej: botón "También en: Congreso" en la ficha de un diputado autonómico).
- [x] **Nuevas Vistas:** Perfil de Partido (/grupo), drill-down de afinidad, comparador de diputados side-by-side, y timelines de actividad.

---

## Fase 2: Herramientas para Periodistas y Power Users

- [ ] **Votaciones "Destacadas" Curadas:** Carrusel manual en portada con las 5 votaciones de mayor impacto, en vez de mostrar un listado cronológico de trámites burocráticos.
- [ ] **Detalle de "Rebeldía" y Tránsfugas:** Mostrar exactamente en qué votaciones un diputado rompió la disciplina de su grupo parlamentario.
- [ ] **Ranking de Asistencia ("Los que menos van"):** Destacar el porcentaje de absentismo ("No Vota") de cada diputado en una vista dedicada de ránkings.
- [ ] **Soporte para Widgets/Embeds (`<iframe>`):** Permitir a la prensa local incrustar el gráfico de "A favor/En contra" de una votación concreta en sus artículos, con enlace de retorno a LQV.
- [ ] **Listado de "Políticas Clave":** Agrupar múltiples votaciones bajo un mismo paraguas (ej. "Reforma Laboral", "Ley de Amnistía").

---

## Fase 3: Deuda Técnica y Robustez (Para aguantar el pico de tráfico)

- [ ] **Completar Scraping CyL:** Asegurar que los scripts de scraping de las Cortes de Castilla y León extraen las fotos y mapean grupos igual de bien que en Andalucía.
- [ ] **Filtros Combinados / Buscador Avanzado:** Permitir buscar combinando (Etiqueta + Rango de Fechas + Proponente + Resultado).
- [ ] **Migrar CSS Monolítico:** Pasar las 1842 líneas de `custom.css` a estilos `scoped` por componente Vue para facilitar el mantenimiento.
- [ ] **Tests E2E y Unitarios:** Cobertura mínima de flujos críticos (Especialmente que el cambio de ámbito a CyL, el buscador y el Quiz no fallen bajo estrés).

---

## Backlog (Largo plazo)

- [ ] **Otras CCAA:** Investigar datos abiertos en Cataluña (parlament.cat), País Vasco (legebiltzarra.eus), Madrid, etc. 19 fuentes distintas en total.
- [ ] **Generación automática de Feeds RSS:** Para seguimiento externo de etiquetas o diputados específicos.
- [ ] **Bookmarks/Favoritos locales:** Usar `localStorage` para guardar políticos "seguidos".
- [ ] **Datos históricos:** Legislaturas I-IX del Congreso (1977-2011), pendientes de digitalización de datos abiertos.
