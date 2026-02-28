# Lo Que Votan - Pendiente

## Completado

- [x] Legislaturas X-XV: scraping completado
- [x] Fotos de diputados: mapeado congreso.es codParlamentario (1259/1259, 100%)
- [x] Optimizar JSON de 80MB: arquitectura 3-tier (manifest 8KB + meta 5MB + votos por legislatura on-demand)
- [x] Agrupar votaciones por expediente en vista de detalle (subTipo, contexto del expediente)
- [x] Diferenciar votaciones del mismo expediente (subTipo + subgrupo)

## Fase 1: Quick wins (1-2 dias) ✓

### UX / Navegacion
- [x] Busqueda global en NavBar (reusar logica de HeroSearch) — elimina el mayor dead-end de navegacion
- [x] Ruta 404 con pagina NotFound — URLs invalidas muestran pagina en blanco
- [x] Hacer badges de grupo clicables (link a /diputados?grupo=X) — dead end actual
- [x] Reordenar columna "Voto" a posicion 2 en historial de diputado — en movil la columna mas importante queda fuera de pantalla

### Accesibilidad / Textos
- [x] Corregir tildes en textos de la UI ("Que vota", "Ultimas votaciones", "mas ajustadas", "mas rebeldes", "mas votados")
- [x] Fix contraste WCAG en badges (badge--leg, badge--proponente) y chips — fallan ratio 4.5:1
- [x] Overrides de dark mode para badge--leg y badge--proponente

### Mobile
- [x] Sticky row labels en tabla de afinidad — al hacer scroll horizontal se pierde el nombre del grupo

### Code quality
- [x] Extraer `votoPillClass` duplicado (VotacionDetail + DiputadoDetail) a utils.js
- [x] Eliminar debounce no-op en VotacionDetail:82
- [x] Actualizar placeholder de HeroSearch para indicar que tambien busca votaciones

## Fase 2: Mejoras medias (3-5 dias) ✓

### Diseno visual
- [x] Cargar web font (Source Sans 3 + DM Serif Display) — headings con serif, body con Source Sans
- [x] Vista cards en movil para tablas de historial (<768px) — responsive-table con data-label en DiputadoDetail y VotacionDetail

### Arquitectura de informacion
- [x] Pagina de perfil de partido/grupo (/grupo/:grupo) — stats agregados, afinidad, rebeldes, miembros con paginacion
- [x] Hint visual sobre AccountabilityCard ("Haz clic en un tema para ver la ficha de rendicion de cuentas")

### Robustez
- [x] Estados de error para fallos de red (retry automatico x2 + ErrorBanner con boton reintentar)
- [x] Limitar DiputadoDetail a cargar solo legislatura actual primero, luego lazy-load las anteriores en background

### Performance
- [x] Verificado: GitHub Pages sirve Content-Encoding: gzip (5MB → 423KB) — no necesita pre-compresion
- [x] Reemplazar datalist de tags en VotacionesView por TagSelect dropdown custom con autocompletado

### Datos
- [x] Re-categorizar textos fallback — verificado: 0 entradas sin clasificar, todas tienen titulo ciudadano

## Fase 3: Features grandes (1-2 semanas)

### Nuevas funcionalidades
- [x] Drill-down desde celda de afinidad ("ver votaciones donde PP y PSOE coincidieron") — /afinidad?ga=X&gb=Y&leg=Z con filtro coinciden/difieren
- [x] Comparador de diputados (/comparar?a=X&b=Y) — side-by-side stats, fotos, VoteBars y votos compartidos
- [x] Timeline de actividad de voto por diputado (sparkline SVG mensual) — barras apiladas favor/contra/abstencion
- [x] Vista alternativa de afinidad en movil (lista rankeada en vez de tabla NxN) — selector de grupo + barras con porcentaje
- [x] Skip-to-content link para accesibilidad con teclado
- [x] Agrupar votaciones por expediente en VotacionesView — toggle checkbox, grupos expandibles
- [x] IDs estables en URLs (legislatura-sesion-numero en vez de indice) — URLs sobreviven regeneracion de datos

### Calidad
- [ ] Tests E2E y unitarios basicos (cobertura minima de flujos criticos)
- [ ] Migrar CSS monolitico (1842 lineas) a estilos scoped por componente

## Fase 4: Analisis Civico y Descubrimiento (Proximamente)

### Alta prioridad / Baja complejidad
- [ ] Votaciones "Destacadas" curadas manualmente para la portada.
- [ ] Buscador de representantes por Provincia / Circunscripcion electoral.
- [ ] Ranking de Asistencia: Destacar el porcentaje de absentismo ("No Vota") de cada diputado.

### Media prioridad / Media complejidad
- [ ] Buscador avanzado / Filtros combinados (Etiqueta + Rango de Fechas + Proponente + Resultado).
- [ ] Detalle de "Rebeldia": Mostrar exactamente en que votaciones un diputado rompio la disciplina de su grupo.

## Fase 5: Herramientas para Periodistas y Power Users (Futuro)

### Media complejidad
- [ ] Listado de "Politicas Clave": Agrupar multiples votaciones bajo un mismo paraguas historico (ej. "Reforma Laboral", "Ley de Amnistia").
- [ ] Generacion automatica de Feeds RSS por etiquetas o por diputado para seguimiento externo.

### Alta complejidad
- [ ] Soporte para Widgets/Embeds: Permitir incrustar graficos de una votacion en medios digitales externos mediante `<iframe>`.

## Fase 6: Gamificacion y Engagement (Largo plazo)

### Alta complejidad (Requiere backend o logica compleja de estado)
- [ ] Quiz de afinidad civica: Cuestionario de 10 votaciones clave reales para descubrir con que partido o diputado coincides mas.

## Backlog (largo plazo)

### CCAA (Comunidades Autonomas)
- [ ] Investigar que parlamentos autonomicos tienen datos abiertos de votaciones
- [ ] Candidatos prioritarios: Cataluna (parlament.cat), Pais Vasco (legebiltzarra.eus), Andalucia (parlamentodeandalucia.es)
- [ ] 17 CCAA + 2 ciudades autonomas = 19 fuentes distintas
- [ ] Reutilizar arquitectura: mismo frontend, scraper adaptado por CCAA, misma categorizacion

### Datos historicos
- [ ] Legislaturas I-IX (1977-2011): no disponibles en datos abiertos, pendiente de digitalizacion

### Otros
- [ ] OG dinamico por diputado/votacion (requiere proxy edge o prerender, no posible con hash routing + GitHub Pages estatico)
- [ ] Bookmarks/favoritos de diputados y temas (localStorage)
