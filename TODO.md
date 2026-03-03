# Lo Que Votan - TODO (pendientes)

Este documento recoge solo trabajo pendiente.

## Cloudflare (cierre operativo)

- [ ] Lanzar un `Update Voting Data` nuevo sobre el último commit de `main` (incluye fix de Andalucía `d5fff21`).
- [ ] Verificar en ese run el paso `Upload raw snapshot to R2 (if configured)` en verde.
- [ ] Verificar en R2 la clave `raw-snapshots/main/latest.tar.gz`.
- [ ] Confirmar que el siguiente run semanal reutiliza snapshot/cache y reduce tiempo total.

## P1 (siguiente bloque)

- [ ] Madrid datos:
  - [ ] Scraping nominal más robusto (reducir heurísticas de `group_votes`).
  - [ ] Mejorar cobertura histórica XII/XI/X.
  - [ ] Mejorar títulos ciudadanos para reducir textos genéricos.
- [ ] AI full-pass de Andalucía para pulir títulos residuales.
- [ ] Añadir filtro por rango de fecha en `/votaciones` (etiqueta/proponente/tipo/legislatura ya están).
- [ ] Ampliar cobertura de tests en flujos críticos sin cobertura suficiente (share/OG dinámico y Worker API).
- [ ] Añadir `source_hash` por votación y exponer trazabilidad completa en API/UI.
- [ ] Completar detección/visualización de tránsfugas o cambios de grupo (rebeldía ya implementada).
- [ ] Glosario institucional contextual (dictamen, voto particular, transaccional, etc.).

## P2 (después)

- [ ] Rendimiento en listados grandes (virtualización + presupuesto LCP/INP).
- [ ] Separar en UI/metodología coincidencia táctica vs alineamiento ideológico.
- [ ] Ficha metodológica pública completa (afinidad + compass + límites/sesgos).
- [ ] Curación continua del banco de preguntas del quiz (más discriminante).
- [ ] Alertas de cambio de postura por partido entre legislaturas.
- [ ] Watchlist ciudadana (diputados/temas).
- [ ] Migrar CSS monolítico restante a estilos por vista/componente.

## Calidad y confianza pública

- [ ] Publicar changelog de metodología/datos por versión.
- [ ] Publicar diff entre actualizaciones en endpoint/página pública (ahora solo en resumen de CI).

## Backlog largo plazo

- [ ] Otras CCAA (Cataluña, País Vasco, C. Valenciana, etc.).
- [ ] Feeds RSS automáticos.
- [ ] Favoritos/bookmarks locales.
- [ ] Históricos I-IX (1977-2011).
