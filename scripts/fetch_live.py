#!/usr/bin/env python3
"""Lee Meta Ads (Graph API) y regenera live.json. Corre solo desde GitHub Actions.

Variables de entorno:
  META_TOKEN   token de usuario del sistema (permiso ads_read) — obligatorio

Cuentas y campañas se descubren solas: toda campaña ACTIVA, o pausada con gasto
en los últimos 30 días, de las dos cuentas que usa Trezco.
"""
import json, os, sys, datetime, zoneinfo, urllib.request, urllib.parse

API = "https://graph.facebook.com/v23.0"
TOKEN = os.environ.get("META_TOKEN", "").strip()
CUENTAS = [
    {"id": "1506077360303279", "nombre": "Grupo Trezco"},
    {"id": "1524284235032951", "nombre": "AURUM APARTMENTS"},
]
RESULT_ACTION = "onsite_conversion.messaging_conversation_started_7d"
TZ = zoneinfo.ZoneInfo("America/Merida")


def get(path, **params):
    params["access_token"] = TOKEN
    url = f"{API}/{path}?{urllib.parse.urlencode(params)}"
    out = []
    while url:
        with urllib.request.urlopen(url, timeout=60) as r:
            d = json.load(r)
        if "data" not in d:
            return d
        out += d["data"]
        url = d.get("paging", {}).get("next")
    return out


def num(x):
    try:
        return float(x)
    except Exception:
        return 0.0


def conv(row):
    for a in row.get("actions", []) or []:
        if a.get("action_type") == RESULT_ACTION:
            return int(num(a.get("value")))
    return 0


def fila(r):
    return {"fecha": r.get("date_start"), "gasto": round(num(r.get("spend")), 2),
            "conversaciones": conv(r), "impresiones": int(num(r.get("impressions"))),
            "clics": int(num(r.get("clicks")))}


def nombre_corto(n):
    # "Tábita · WhatsApp · Prueba Sep-2026" -> "Tábita"; eventos conservan su segundo tramo
    partes = [p.strip() for p in n.split("·")]
    dev = partes[0]
    if len(partes) > 1 and partes[1].upper() not in ("WHATSAPP",):
        return f"{dev} · {partes[1].title()}"
    return dev


def main():
    if not TOKEN:
        sys.exit("Falta META_TOKEN")
    hoy = datetime.datetime.now(TZ).date()
    desde7 = hoy - datetime.timedelta(days=6)
    campanas = []
    for cta in CUENTAS:
        lista = get(f"act_{cta['id']}/campaigns",
                    fields="id,name,effective_status,daily_budget,lifetime_budget,spend_cap,start_time,stop_time",
                    filtering=json.dumps([{"field": "effective_status", "operator": "IN",
                                           "value": ["ACTIVE", "PAUSED", "CAMPAIGN_PAUSED"]}]),
                    limit=100)
        if isinstance(lista, dict):
            sys.exit(f"Error de Meta en {cta['nombre']}: {lista}")
        for c in lista:
            cid = c["id"]
            tot = get(f"{cid}/insights", fields="spend,impressions,clicks,actions", date_preset="maximum")
            tot = fila(tot[0]) if tot else {"gasto": 0, "conversaciones": 0, "impresiones": 0, "clics": 0}
            tot.pop("fecha", None)
            rec = get(f"{cid}/insights", fields="spend", time_range=json.dumps({"since": str(desde7), "until": str(hoy)}))
            gasto7 = num(rec[0]["spend"]) if rec else 0
            fin = (c.get("stop_time") or "")[:10]
            terminada = bool(fin) and fin < str(hoy)
            if c["effective_status"] != "ACTIVE" and gasto7 <= 0:
                continue
            if terminada and gasto7 <= 0:
                continue
            dias = get(f"{cid}/insights", fields="spend,impressions,clicks,actions,date_start",
                       time_range=json.dumps({"since": str(desde7), "until": str(hoy)}), time_increment=1)
            por_fecha = {r["date_start"]: fila(r) for r in dias}
            serie = []
            for i in range(7):
                f = str(desde7 + datetime.timedelta(days=i))
                serie.append(por_fecha.get(f, {"fecha": f, "gasto": 0.0, "conversaciones": 0, "impresiones": 0, "clics": 0}))
            autorizado = num(c.get("spend_cap")) / 100 if c.get("spend_cap") else (num(c.get("lifetime_budget")) / 100 if c.get("lifetime_budget") else 0)
            campanas.append({
                "id": cid, "nombre": nombre_corto(c["name"]), "nombreCompleto": c["name"],
                "cuenta": cta["nombre"], "autorizado": round(autorizado),
                "estado": "ENDED" if terminada else c["effective_status"],
                "presupuestoDiario": num(c.get("daily_budget")) / 100 if c.get("daily_budget") else 0,
                "fin": fin,
                "acumulado": tot, "dias": serie,
            })
    orden = {"tabita": 0, "ameka": 1, "aurum": 2}
    import unicodedata
    def key(c):
        n = unicodedata.normalize("NFD", c["nombre"].lower()).encode("ascii", "ignore").decode()
        base = n.split("·")[0].strip()
        return (orden.get(base, 9), 1 if "·" in n else 0, c["nombre"])
    campanas.sort(key=key)
    out = {"actualizado": datetime.datetime.now(TZ).isoformat(timespec="minutes"),
           "fuente": "Meta Ads · conversaciones de WhatsApp iniciadas (7 días)",
           "automatico": True, "campanas": campanas}
    json.dump(out, open("live.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("ok", len(campanas), "campañas", out["actualizado"])


if __name__ == "__main__":
    main()
