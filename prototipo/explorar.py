"""Exploracion de la muestra: consistencia entre metadatos y texto (apoyo al Cap. 0 y Cap. 6)."""
import collections as C
import glob
import json
import re

H = [json.load(open(f, encoding="utf-8")) for f in sorted(glob.glob("datos/historias/*.json"))]
resp = C.Counter()
for h in H:
    t = h["texto"]
    if not t:
        continue
    f = re.search(r"FACTURACI.N\n(.*?)\n\n", t, re.S).group(1)
    mv = re.search(r"\$\s?([\d.,]+)", f)
    val = int(re.sub(r"[.,]", "", mv.group(1))) if mv else None
    mp = re.search(r"\((\d{6})\)", f)
    me = re.search(r"pago: (.*?)\.(\n|$)", f)
    bad = []
    if val != h["valor_cop"]:
        bad.append(("valor", val, h["valor_cop"]))
    if not mp or mp.group(1) != h["procedimiento"]:
        bad.append(("proc", mp and mp.group(1), h["procedimiento"]))
    if not me or me.group(1) != h["eps"]:
        bad.append(("eps", me and me.group(1), h["eps"]))
    if h["fecha_radicacion"] < h["fecha_atencion"]:
        bad.append("fecha")
    if bad:
        print(h["id"], bad)
    r = re.search(r"RESPONSABLE DE LA ATENCI.N\n(.*?)(\n\n|$)", t, re.S).group(1)
    r = re.sub(r"\d+", "N", r)
    r = re.sub(r"[A-ZÁÉÍÓÚ][a-záéíóúñ]+ [A-ZÁÉÍÓÚ][a-záéíóúñ]+( [A-ZÁÉÍÓÚ][a-záéíóúñ]+)?", "NOMBRE", r)
    resp[r[:160]] += 1
for k, n in resp.most_common(12):
    print(n, k.replace("\n", " | "))
print(C.Counter(h["fecha_radicacion"] for h in H).most_common(12))
print(C.Counter(h["fecha_atencion"][:7] for h in H))
