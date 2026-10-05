#!/usr/bin/env python3
"""Construye live.json a partir de resultados crudos de Meta (ads_get_ad_entities).

Uso:
  python3 scripts/build_live.py --daily archivo1.json [archivo2.json ...] --total archivoA.json [archivoB.json ...] --out live.json

Cada archivo es el resultado del tool tal cual ({"ad_entities": "<json>"}) o una lista ya decodificada.
--daily: filas por día (time_increment=1) de los últimos 7 días.
--total: filas acumuladas (date_preset=maximum) por campaña.
"""
import json, sys, argparse, datetime, zoneinfo

CAMPANAS = [
  {"id":"120251063801410373","nombre":"Tábita","cuenta":"Grupo Trezco","autorizado":9000},
  {"id":"120251063806180373","nombre":"Ameka","cuenta":"Grupo Trezco","autorizado":7500},
  {"id":"120251277642690072","nombre":"Aurum","cuenta":"AURUM APARTMENTS","autorizado":5600},
]

def load(p):
    d=json.load(open(p,encoding='utf-8'))
    if isinstance(d,dict) and 'ad_entities' in d:
        d=d['ad_entities']
        if isinstance(d,str): d=json.loads(d)
    return d

def num(x):
    try: return float(x)
    except: return 0.0

def results(e):
    r=e.get('results') or {}
    vals=r.get('values')
    if vals: return int(num(vals[0].get('value')))
    return 0

def row(e):
    return {"fecha":e.get('date_start'),"gasto":round(num(e['amount_spent']['value']),2),
            "conversaciones":results(e),"impresiones":int(num(e.get('impressions'))),"clics":int(num(e.get('clicks')))}

ap=argparse.ArgumentParser(); ap.add_argument('--daily',nargs='+',required=True); ap.add_argument('--total',nargs='+',required=True); ap.add_argument('--out',default='live.json')
a=ap.parse_args()
daily=[e for p in a.daily for e in load(p)]
total=[e for p in a.total for e in load(p)]
tz=zoneinfo.ZoneInfo('America/Merida'); now=datetime.datetime.now(tz)
out={"actualizado":now.isoformat(timespec='minutes'),"fuente":"Meta Ads · conversaciones de WhatsApp iniciadas (7 días)","campanas":[]}
for c in CAMPANAS:
    dd=sorted([row(e) for e in daily if e.get('id')==c['id']],key=lambda r:r['fecha'])
    tt=[e for e in total if e.get('id')==c['id']]
    est=next((e.get('effective_status') for e in daily if e.get('id')==c['id'] and e.get('effective_status')),'')
    pres=next((num(e.get('daily_budget',{}).get('value')) for e in daily if e.get('id')==c['id'] and e.get('daily_budget')),0)
    acc=row(tt[0]) if tt else {"gasto":0,"conversaciones":0,"impresiones":0,"clics":0}
    acc.pop('fecha',None)
    out['campanas'].append({**c,"estado":est,"presupuestoDiario":pres,"acumulado":acc,"dias":dd})
json.dump(out,open(a.out,'w',encoding='utf-8'),ensure_ascii=False,indent=1)
print('ok',a.out,now.isoformat(timespec='minutes'))
