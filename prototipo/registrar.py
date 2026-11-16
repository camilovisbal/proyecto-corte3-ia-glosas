"""Registra el equipo UNA sola vez y guarda el token fuera del repositorio.

El token no se imprime: solo se muestra su longitud.
"""
import json
import pathlib
import sys

import requests

from comun import API, RUTA_TOKEN

if RUTA_TOKEN.exists():
    sys.exit(f"Ya existe un token en {RUTA_TOKEN}; no se registra de nuevo.")

cuerpo = {"nombre": "visbal-glosas", "integrantes": ["Camilo Andrés Visbal Beltrán"]}
r = requests.post(f"{API}/equipos", json=cuerpo, timeout=30)
try:
    datos = r.json()
except ValueError:
    sys.exit(f"HTTP {r.status_code}: respuesta no JSON")

token = None
if isinstance(datos, dict):
    for k in ("token", "access_token", "bearer"):
        if datos.get(k):
            token = datos[k]
            break

if r.status_code in (200, 201) and token:
    RUTA_TOKEN.parent.mkdir(parents=True, exist_ok=True)
    RUTA_TOKEN.write_text(token, encoding="utf-8")
    visible = {k: ("<oculto, longitud %d>" % len(v) if v == token else v) for k, v in datos.items()}
    pathlib.Path(__file__).with_name("registro_equipo.json").write_text(
        json.dumps(visible, indent=2, ensure_ascii=False), encoding="utf-8")
    print("HTTP", r.status_code, json.dumps(visible, ensure_ascii=False))
else:
    print("HTTP", r.status_code, json.dumps(datos, ensure_ascii=False)[:800])
