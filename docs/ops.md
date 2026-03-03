# Operacion de pipelines (Cloudflare + datos)

Ultima actualizacion: 2026-03-03.

## SLO objetivo (fase inicial)

- `Update Voting Data` incremental (`full_history=false`): <= 120 min.
- `Cloudflare Data Sync` por scopes cambiados: <= 30 min.
- `Deploy to Cloudflare` tras CI en `main`: <= 10 min.

## Criterio de alerta

- Alertar cuando una ejecucion supere `1.5x` su baseline de referencia.
- Alertar cuando haya 2 fallos consecutivos del mismo workflow.
- Alertar cuando `Update Voting Data` no genere commit de datos durante 2 ciclos semanales seguidos (posible rotura de scraping/fuentes).

## Baseline capturado (provisional)

Nota: baseline definitivo pendiente de 3 lunes consecutivos con ejecucion programada estable.

### Update Voting Data

- Run `22622247625` (2026-03-03, manual): `45m 23s` (success).
- Run `22582693900` (2026-03-02, manual): `cancelled`.
- Run `22564932038` (2026-03-02, scheduled): `failure`.

Baseline provisional actual:
- `~45 min` para incremental exitoso con actividad de scraping/transform.

### Cloudflare Data Sync

Runs exitosos recientes:
- `22623840699` (2026-03-03): `43s`
- `22620757730` (2026-03-03): `44s`
- `22616802869` (2026-03-03): `42s`
- `22616247978` (2026-03-03): `44s`
- `22614898151` (2026-03-03): `38s`

Baseline actual:
- `~42s` (rango observado 38s-44s).

## Evidencias operativas clave

- Snapshot raw subido a R2 en run `22622247625`:
- `raw-snapshots/main/20260303T125159Z-e12fc8877308.tar.gz`
- `raw-snapshots/main/latest.tar.gz`
- Subida R2 en modo remoto verificada (fix `--remote`) en run `22624881347`:
- `Resource location: remote`
- `d1-seeds/20260303T132207Z-2bab02625c4f.sql.gz`
- Trigger de sync por scopes detectados en run `22622247625`:
- `andalucia,cyl,madrid,nacional`
- Produccion validada tras sync manual:
- `/api/health` -> `backend: d1+assets`
- `/api/votaciones?scope=andalucia&page=1&pageSize=1` -> `source: d1`

## Proximos cierres operativos

- Confirmar en un run incremental posterior que `Restore raw data cache` y/o `Restore raw snapshot from R2` se reutiliza correctamente.
- Consolidar baseline con 3 lunes seguidos y ajustar SLO si hay variabilidad estructural.
