# Trezco Campañas

Reporte de campañas de Trezco Master Broker. Sitio estático: `index.html` (app) + `data.json` (datos por periodo).

Para un reporte nuevo: editar `data.json` (agregar un elemento a `periodos`). El diseño no se toca.

## Live
`live.json` alimenta la pestaña **Live** (últimos 7 días por campaña, directo de Meta Ads). Se regenera con
`python3 scripts/build_live.py --daily <filas por día> --total <acumulados> --out live.json` a partir de los resultados crudos de `ads_get_ad_entities` y se publica con un push a `main`.

## Estructura (nov 2026)
6 pestañas: Resumen · Live · Desarrollos (incluye indicadores, anuncios y eventos) · Leads (embudo, respuesta y Odoo en vivo) · Plan y presupuesto (plan, presupuesto, calendario) · Decisiones. Las vistas viejas siguen accesibles por #indicadores, #embudo, #respuesta, #anuncios, #eventos, #presupuesto, #calendario, #evidencia.
El Resumen compara cada número con el periodo anterior de `data.json` y muestra la banda "Desde el día 1" (acumulado de todos los periodos).

## Datos automáticos
`.github/workflows/live.yml` corre cada 3 h: `scripts/fetch_live.py` (Meta → live.json) y `scripts/fetch_odoo.py` (Odoo → leads.json). Secrets: META_TOKEN, ODOO_LOGIN, ODOO_API_KEY.
