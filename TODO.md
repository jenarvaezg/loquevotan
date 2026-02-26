# Congreso Transparente - Pendiente

## Próximos pasos

### CCAA (Comunidades Autónomas)
- [ ] Investigar qué parlamentos autonómicos tienen datos abiertos de votaciones
- [ ] Candidatos prioritarios: Cataluña (parlament.cat), País Vasco (legebiltzarra.eus), Andalucía (parlamentodeandalucia.es)
- [ ] 17 CCAA + 2 ciudades autónomas = 19 fuentes distintas
- [ ] Reutilizar arquitectura: mismo frontend, scraper adaptado por CCAA, misma categorización Gemini

### Datos históricos
- [ ] Legislaturas I-IX (1977-2011): no disponibles en datos abiertos, pendiente de digitalización
- [ ] Legislaturas XI-XIV: pendientes de scraping (solo X y XV descargadas)

### Mejoras frontend
- [ ] Optimizar JSON de 18MB (gzip, paginación server-side, o split por legislatura)
- [ ] Re-categorizar los ~380 textos fallback (lotes de Gemini que fallaron)
