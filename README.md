# Trezco Campañas

Reporte de campañas de Trezco Master Broker. Sitio estático: `index.html` (app) + `data.json` (datos por periodo).

Para un reporte nuevo: editar `data.json` (agregar un elemento a `periodos`). El diseño no se toca.

## Live
`live.json` alimenta la pestaña **Live** (últimos 7 días por campaña, directo de Meta Ads). Se regenera con
`python3 scripts/build_live.py --daily <filas por día> --total <acumulados> --out live.json` a partir de los resultados crudos de `ads_get_ad_entities` y se publica con un push a `main`.
