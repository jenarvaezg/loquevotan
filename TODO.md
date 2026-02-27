# Congreso Transparente - Pendiente

## Próximos pasos

### CCAA (Comunidades Autónomas)
- [ ] Investigar qué parlamentos autonómicos tienen datos abiertos de votaciones
- [ ] Candidatos prioritarios: Cataluña (parlament.cat), País Vasco (legebiltzarra.eus), Andalucía (parlamentodeandalucia.es)
- [ ] 17 CCAA + 2 ciudades autónomas = 19 fuentes distintas
- [ ] Reutilizar arquitectura: mismo frontend, scraper adaptado por CCAA, misma categorización Gemini

### Datos históricos
- [ ] Legislaturas I-IX (1977-2011): no disponibles en datos abiertos, pendiente de digitalización
- [x] Legislaturas XI-XIV: pendientes de scraping → completado (X-XV descargadas)

### Mejoras datos
- [ ] Diferenciar votaciones sobre el mismo textoExpediente (enmiendas, artículos, votación final) — actualmente comparten título ciudadano porque el texto parlamentario es idéntico
- [ ] Re-categorizar los ~80 textos fallback (lotes que fallaron)
- [x] Fotos de diputados: mapeado congreso.es codParlamentario (1259/1259, 100%)

### Mejoras frontend
- [ ] Optimizar JSON de 77MB (gzip, paginación server-side, o split por legislatura)
- [ ] Git LFS para votaciones.json
- [ ] OG dinámico por diputado/votación (requiere proxy edge o prerender, no posible con hash routing + GitHub Pages estático)
