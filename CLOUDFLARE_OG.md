# OG dinámico con Cloudflare Workers

Este proyecto incluye un Worker que genera metatags Open Graph/Twitter en runtime para enlaces compartidos y luego redirige a la SPA.

## Rutas de share soportadas

- `/share/votacion/:scope/:id`
- `/share/diputado/:scope/:name`

Ejemplos:

- `https://dondevotan.es/share/votacion/nacional/XV-120-3`
- `https://dondevotan.es/share/diputado/cyl/Juan%20P%C3%A9rez`

## Cómo funciona

1. El bot de red social abre `/share/...`.
2. El Worker lee `data/*/votaciones_meta.json` desde `ASSETS` y genera OG tags.
3. Para usuarios reales, el HTML incluye redirección a rutas limpias (`/votacion/...`, `/diputado/...`) y fija `preferredScope` en `localStorage`.

## Deploy

1. Build frontend:

```bash
npm run build
```

2. Deploy Worker + assets:

```bash
npx wrangler deploy
```

## Configuración

Archivo: `wrangler.toml`

- `assets.directory = "./dist"`
- `assets.run_worker_first = ["/share/*"]`
- `vars.SITE_URL = "https://dondevotan.es"`

Variable opcional:

- `OG_IMAGE_URL` para sobrescribir la imagen OG global.

## Nota sobre base path

`vite.config.js` ahora usa `VITE_BASE_PATH` (default `/`).

- Dominio propio: no hace falta variable (usa `/`).
- Si vuelves a subruta (ej. GitHub Pages): usar `VITE_BASE_PATH=/loquevotan/`.
