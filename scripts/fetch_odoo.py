#!/usr/bin/env python3
"""Lee los leads de Odoo (CRM) y genera leads.json. Corre solo desde GitHub Actions.

Variables de entorno:
  ODOO_URL      https://trezco.odoo.com (default)
  ODOO_DB       nombre de la base (default: trezco)
  ODOO_LOGIN    correo del usuario
  ODOO_API_KEY  clave de API del usuario (Preferencias → Seguridad de la cuenta)
"""
import json, os, sys, datetime, zoneinfo, xmlrpc.client, unicodedata, collections

URL = os.environ.get("ODOO_URL", "https://trezco.odoo.com").rstrip("/")
DB = os.environ.get("ODOO_DB", "trezco")
LOGIN = os.environ.get("ODOO_LOGIN", "")
KEY = os.environ.get("ODOO_API_KEY", "")
TZ = zoneinfo.ZoneInfo("America/Merida")
DESDE = "2026-09-10"  # arranque de las campañas

ETAPAS = ["Nuevo Lead", "Contactados", "Primer mensaje", "Primera llamada", "Cita Agendada", "Apartado", "Ganado", "Perdido"]
TAGS = {"caliente": "calientes", "tibio": "tibios", "frio": "frios", "no califica": "nocalifica"}


def norm(s):
    s = unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return "".join(ch for ch in s if ch.isalnum() or ch == " ").strip()


def desarrollo(camp):
    n = norm(camp)
    for k in ("tabita", "ameka", "aurum"):
        if k in n:
            return k
    if "organico" in n:
        return "organico"
    return "sin"


def main():
    if not (LOGIN and KEY):
        sys.exit("Faltan ODOO_LOGIN / ODOO_API_KEY")
    common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
    uid = common.authenticate(DB, LOGIN, KEY, {})
    if not uid:
        sys.exit("Odoo rechazó las credenciales")
    m = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")

    def call(model, method, *args, **kw):
        return m.execute_kw(DB, uid, KEY, model, method, list(args), kw)

    leads = call("crm.lead", "search_read", [["create_date", ">=", DESDE]],
                 fields=["create_date", "campaign_id", "stage_id", "tag_ids", "user_id", "source_id", "medium_id", "active"],
                 context={"active_test": False})
    tag_ids = sorted({t for l in leads for t in l["tag_ids"]})
    tags = {t["id"]: t["name"] for t in call("crm.tag", "read", tag_ids, fields=["name"])} if tag_ids else {}

    hoy = datetime.datetime.now(TZ).date()
    por_dev = collections.defaultdict(lambda: {
        "leads": 0, "etapas": collections.Counter(), "calientes": 0, "tibios": 0, "frios": 0, "nocalifica": 0,
        "sinEtiqueta": 0, "conAsesor": 0, "citas": 0, "perdidos": 0, "interesados": 0, "porAsesor": collections.Counter(),
    })
    diario = collections.Counter()
    mensual = collections.defaultdict(collections.Counter)
    for l in leads:
        dev = desarrollo(l["campaign_id"][1] if l["campaign_id"] else "")
        d = por_dev[dev]
        d["leads"] += 1
        etapa = l["stage_id"][1] if l["stage_id"] else "Sin etapa"
        d["etapas"][etapa] += 1
        ne = norm(etapa)
        if "cita" in ne or "apartado" in ne or "ganado" in ne:
            d["citas"] += 1
        if "perdido" in ne:
            d["perdidos"] += 1
        tnames = [norm(tags.get(t, "")) for t in l["tag_ids"]]
        matched = False
        for t in tnames:
            for k, campo in TAGS.items():
                if k in t:
                    d[campo] += 1
                    matched = True
        if not matched:
            d["sinEtiqueta"] += 1
        if any(("caliente" in t or "tibio" in t) for t in tnames):
            d["interesados"] += 1
        asesor = l["user_id"][1] if l["user_id"] else "Sin asesor"
        d["porAsesor"][asesor] += 1
        if l["user_id"] and norm(asesor) != "rodrigo avila":
            d["conAsesor"] += 1
        fecha = l["create_date"][:10]
        diario[fecha] += 1
        mensual[fecha[:7]][dev] += 1

    orden = ["tabita", "ameka", "aurum", "organico", "sin"]
    nombres = {"tabita": "Tábita", "ameka": "Ameka", "aurum": "Aurum", "organico": "Orgánico", "sin": "Sin campaña"}
    desarrollos = []
    for k in orden:
        if k not in por_dev:
            continue
        d = por_dev[k]
        desarrollos.append({
            "id": k, "nombre": nombres[k], "leads": d["leads"], "interesados": d["interesados"],
            "calientes": d["calientes"], "tibios": d["tibios"], "frios": d["frios"], "nocalifica": d["nocalifica"],
            "sinEtiqueta": d["sinEtiqueta"], "conAsesor": d["conAsesor"], "citas": d["citas"], "perdidos": d["perdidos"],
            "etapas": [{"nombre": e, "valor": d["etapas"].get(e, 0)} for e in ETAPAS if d["etapas"].get(e, 0)] +
                      [{"nombre": e, "valor": v} for e, v in d["etapas"].items() if e not in ETAPAS],
            "porAsesor": dict(d["porAsesor"].most_common()),
        })
    campana = [x for x in desarrollos if x["id"] in ("tabita", "ameka", "aurum")]
    tot = {k: sum(x[k] for x in campana) for k in ("leads", "interesados", "calientes", "tibios", "frios", "nocalifica", "conAsesor", "citas", "perdidos")}
    ult14 = [(str(hoy - datetime.timedelta(days=i))) for i in range(13, -1, -1)]
    out = {
        "actualizado": datetime.datetime.now(TZ).isoformat(timespec="minutes"),
        "fuente": "Odoo CRM · leads creados desde el 10 sep 2026",
        "automatico": True,
        "desde": DESDE,
        "totalCampanas": tot,
        "desarrollos": desarrollos,
        "ultimos14": [{"fecha": f, "leads": diario.get(f, 0)} for f in ult14],
        "mensual": [{"mes": mes, **{nombres[k]: v for k, v in c.items()}} for mes, c in sorted(mensual.items())],
    }
    json.dump(out, open("leads.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("ok", len(leads), "leads", out["actualizado"])


if __name__ == "__main__":
    main()
