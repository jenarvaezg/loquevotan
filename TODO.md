# Lo Que Votan - TODO (pendientes)

Este documento recoge solo trabajo pendiente.

## P0 (hacer ahora)

- [x] Pipeline CI de datos:
  - [x] Ejecutar `npm run test:data-integrity` en PR.
  - [x] Añadir checks de estructura/tamaño de artefactos de datos.
- [x] Homogeneizar `run_update.py` con política fail-fast para evitar publicar datasets parciales.
- [x] Mostrar fecha de última actualización por ámbito en UI.
- [x] Generar diff automático entre actualizaciones (votaciones nuevas, recategorizaciones, cambios sensibles).
- [x] Completar soporte de widgets/embeds para distribución en prensa y terceros.
- [x] Definir y arrancar migración de datos a Cloudflare (D1/R2 + Worker API + job semanal).

## P1 (siguiente bloque)

- [ ] Madrid datos:
  - [ ] Bypass/scraping más robusto para votos nominales.
  - [ ] Históricos XII/XI/X.
  - [ ] AI pass de títulos ciudadanos.
- [ ] AI full-pass de Andalucía para limpiar títulos crípticos.
- [ ] Filtros combinados/buscador avanzado (etiqueta + fecha + proponente).
- [ ] Cobertura de tests E2E/unit en flujos críticos pendientes.
- [ ] Trazabilidad por votación (`source_url` + `source_hash`).
- [ ] Accesibilidad automatizada en CI (`axe`) en vistas clave.
- [ ] Completar detalle de rebeldía/tránsfugas en perfil de diputado.
- [ ] Glosario institucional contextual (dictamen, voto particular, transaccional, etc.).

## P2 (después)

- [ ] Rendimiento en listados grandes (virtualización + presupuesto LCP/INP).
- [ ] Changelog público de metodología y datos por release.
- [ ] Separar en UI/metodología coincidencia táctica vs alineamiento ideológico.
- [ ] Ficha metodológica pública completa (afinidad + compass + límites/sesgos).
- [ ] Curación continua del banco de preguntas del quiz (más discriminante).
- [ ] Alertas de cambio de postura por partido entre legislaturas.
- [ ] Watchlist ciudadana (diputados/temas).
- [ ] Migrar CSS monolítico restante a estilos por vista/componente.

## Epics técnicos

### Migración de datos a Cloudflare (D1/R2 + Worker API)

- [x] Diseñar esquema D1 por ámbito (`votaciones`, `vot_results`, `votos_nominales`, `diputados`).
- [x] Mantener R2 para raw/snapshots/exports grandes.
- [x] Exponer API Worker (`/api/votaciones`, `/api/votacion/:id`, `/api/diputado/:id`) con paginación y cache HTTP.
- [ ] Adaptar transforms/run_update para upsert incremental en D1.
- [x] Programar job semanal end-to-end con checks de integridad y rollback.
- [x] Plan de convivencia y rollback durante transición (híbrido JSON + API).

### Calidad y confianza pública

- [ ] Publicar changelog de metodología/datos por versión.
- [ ] Exponer trazabilidad por votación (fuente + hash).
- [ ] Publicar resumen de diff entre actualizaciones.

## Backlog largo plazo

- [ ] Otras CCAA (Cataluña, País Vasco, C. Valenciana, etc.).
- [ ] Feeds RSS automáticos.
- [ ] Favoritos/bookmarks locales.
- [ ] Históricos I-IX (1977-2011).
