# OG dinámico + API/embeds con Cloudflare Workers

Este proyecto incluye un Worker que genera metatags Open Graph/Twitter en runtime para enlaces compartidos y luego redirige a la SPA.

## Rutas de share soportadas

- `/share/votacion/:scope/:id`
- `/share/diputado/:scope/:name`
- `/og/votacion/:scope/:id` (imagen OG dinámica, por defecto PNG para compatibilidad con scrapers)
- `/og/diputado/:scope/:name` (imagen OG dinámica SVG con foto + badge de partido)
- `/api/health`
- `/api/scopes`
- `/api/votaciones?scope=nacional&page=1&pageSize=20`
- `/api/votacion/:scope/:id`
- `/api/diputado/:scope/:name`

Parámetros opcionales en votación para contextualizar el share:

- `?dip=<Nombre>&vote=<si|no|abstencion|no_vota>`
- `?group=<Grupo>&groupVote=<si|no|abstencion|no_vota>`

Ejemplos:

- `https://loquevotan.es/share/votacion/nacional/XV-13-1`
- `https://loquevotan.es/share/diputado/cyl/Juan%20P%C3%A9rez`

## Widgets / embebidos para prensa

Desde una votación concreta, el botón "Insertar en web" genera un iframe con:

- URL estable con ámbito explícito: `/widget/:scope/:id?embed=true`
- auto-resize por `postMessage` (`lqv:embed:resize`) para evitar cortes
- `loading="lazy"` + `referrerpolicy` seguro para terceros

Ejemplo de embed:

```html
<iframe src="https://loquevotan.es/widget/nacional/XV-164-20?embed=true" width="100%" height="420" frameborder="0" scrolling="no" loading="lazy" referrerpolicy="strict-origin-when-cross-origin" style="border:1px solid #e2e8f0; border-radius:12px; max-width:550px;"></iframe>
```

## Cómo funciona

1. El bot de red social abre `/share/...`.
2. El Worker lee `data/*/votaciones_meta.json` desde `ASSETS` y genera OG tags.
   - En rutas de votación, `og:image` apunta a `/og/votacion/:scope/:id?format=png` y se genera al vuelo (hemiciclo + resumen visual de votos). Si el share incluye `group=...`, añade badge/logo del partido.
   - Si el share incluye `dip=...`, el PNG añade mini foto real del diputado (si está disponible) con badge de partido.
   - En rutas de diputado, `og:image` apunta a `/og/diputado/:scope/:name` y se genera al vuelo (foto + badge/logo de partido + métricas).
3. Para usuarios reales, el HTML incluye redirección a rutas limpias (`/votacion/...`, `/diputado/...`) y fija `preferredScope` en `localStorage`.

## API pública (fase de migración)

La API del Worker expone una capa estable para migrar del frontend basado en JSON estático hacia backend en Cloudflare:

- `GET /api/scopes`: ámbitos disponibles
- `GET /api/votaciones`: listado paginado y filtrable (`q`, `leg`, `tag`, `from`, `to`, `page`, `pageSize`)
- `GET /api/votacion/:scope/:id`: detalle de una votación
- `GET /api/diputado/:scope/:name`: perfil y métricas agregadas

Hoy estos endpoints leen `ASSETS` (`public/data/*`) y se cachean en edge.
El contrato queda listo para cambiar backend a D1 sin romper consumidores.

## D1: esquema y sync semanal (arranque de migración)

Archivos nuevos:

- `cloudflare/d1/schema.sql`: esquema base (`scope_meta`, `groups`, `votaciones`, `diputados`)
- `scripts/cloudflare/build_d1_seed.mjs`: snapshot SQL desde `public/data`
- `.github/workflows/cloudflare-data-sync.yml`: job semanal/manual que:
  - genera snapshot SQL,
  - sube artifact,
  - aplica `schema.sql` + snapshot en D1 si están configurados secrets.

Comando local para generar seed:

```bash
npm run cf:d1:seed
```

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
- `CLOUDFLARE_D1_DATABASE_NAME` (solo para sync de datos a D1)

Permisos mínimos recomendados para el token:

- `Account` -> `Cloudflare Workers Scripts:Edit`
- `Zone` -> `Workers Routes:Edit`
- `Zone` -> `Zone Settings:Read`
- `Account` -> `D1:Edit`

## Configuración

Archivo: `wrangler.toml`

- `assets.directory = "./dist"`
- `assets.run_worker_first = ["/share/*", "/og/*", "/api/*"]`
- `vars.SITE_URL = "https://loquevotan.es"`

Variable opcional:

- `OG_IMAGE_URL` para sobrescribir la imagen OG de fallback (casos no encontrados y perfiles sin foto).

## Nota sobre base path

`vite.config.js` ahora usa `VITE_BASE_PATH` (default `/`).

- Dominio propio: no hace falta variable (usa `/`).
- Si vuelves a subruta (ej. GitHub Pages): usar `VITE_BASE_PATH=/loquevotan/`.
