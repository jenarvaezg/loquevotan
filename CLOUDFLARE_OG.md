# OG dinámico con Cloudflare Workers

Este proyecto incluye un Worker que genera metatags Open Graph/Twitter en runtime para enlaces compartidos y luego redirige a la SPA.

## Rutas de share soportadas

- `/share/votacion/:scope/:id`
- `/share/diputado/:scope/:name`
- `/og/votacion/:scope/:id` (imagen OG dinámica SVG)

Ejemplos:

- `https://loquevotan.es/share/votacion/nacional/XV-13-1`
- `https://loquevotan.es/share/diputado/cyl/Juan%20P%C3%A9rez`

## Cómo funciona

1. El bot de red social abre `/share/...`.
2. El Worker lee `data/*/votaciones_meta.json` desde `ASSETS` y genera OG tags.
   - En rutas de votación, `og:image` apunta a `/og/votacion/:scope/:id` y se genera al vuelo (hemiciclo + resumen de votos).
   - En rutas de diputado, usa `dipFotos` como `og:image` cuando hay foto disponible.
3. Para usuarios reales, el HTML incluye redirección a rutas limpias (`/votacion/...`, `/diputado/...`) y fija `preferredScope` en `localStorage`.

## Deploy

1. Build frontend:

```bash
npm run build
```

2. Preparar assets para Cloudflare (divide `votos_*.json` > 25 MiB):

```bash
npm run cf:prepare-assets
```

3. Deploy Worker + assets:

```bash
npx wrangler deploy
```

## Deploy automático con GitHub Actions

El workflow `.github/workflows/deploy.yml` despliega a Cloudflare en cada push a `main`.
Incluye automáticamente el paso `cf:prepare-assets` para evitar errores de límite por archivo.

Configura estos secrets en GitHub (`Settings` -> `Secrets and variables` -> `Actions`):

- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`

Permisos mínimos recomendados para el token:

- `Account` -> `Cloudflare Workers Scripts:Edit`
- `Zone` -> `Workers Routes:Edit`
- `Zone` -> `Zone Settings:Read`

## Configuración

Archivo: `wrangler.toml`

- `assets.directory = "./dist"`
- `assets.run_worker_first = ["/share/*"]`
- `vars.SITE_URL = "https://loquevotan.es"`

Variable opcional:

- `OG_IMAGE_URL` para sobrescribir la imagen OG de fallback (casos no encontrados y perfiles sin foto).

## Nota sobre base path

`vite.config.js` ahora usa `VITE_BASE_PATH` (default `/`).

- Dominio propio: no hace falta variable (usa `/`).
- Si vuelves a subruta (ej. GitHub Pages): usar `VITE_BASE_PATH=/loquevotan/`.
