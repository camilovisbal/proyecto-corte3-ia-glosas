"""Explora el formato de los campos extra del cuerpo (tokens, modelos) sin calificar.

Cada prueba lleva una ultima prediccion con «riesgo» invalido, asi que la API nunca la califica;
solo interesa el mensaje de validacion que devuelve antes de llegar a esa prediccion.
Uso: python validar_formato.py '<json con los campos extra>' ...
"""
import json
import sys

from comun import API, sesion

s = sesion()
for extra in sys.argv[1:]:
    preds = [{"id": i, "riesgo": "bajo"} for i in range(1, 301)]
    preds[-1]["riesgo"] = "zzz"
    cuerpo = {"predicciones": preds, **json.loads(extra)}
    r = s.post(f"{API}/priorizacion", json=cuerpo, timeout=60)
    print(extra, "->", r.status_code, r.text[:200])
    if r.status_code == 200:
        sys.exit("ATENCION: cuerpo aceptado")
