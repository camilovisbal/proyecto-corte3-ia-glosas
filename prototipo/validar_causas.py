"""Descubre el vocabulario de «causa» que acepta la API sin gastar envios.

La causa candidata va en la primera prediccion y la ultima lleva un «riesgo» invalido: si la causa es
valida, la API rechaza el cuerpo por el «riesgo» de la ultima; si no, por la causa. Nunca se califica.
"""
import sys

from comun import API, sesion

s = sesion()
candidatos = sys.argv[1:]
for c in candidatos:
    preds = [{"id": i, "riesgo": "revisar" if i == 1 else "bajo", **({"causa": c} if i == 1 else {})}
             for i in range(1, 301)]
    preds[-1]["riesgo"] = "zzz"  # invalida a proposito la ULTIMA prediccion: nunca se califica
    cuerpo = {"predicciones": preds, "tokens_entrada": 1, "tokens_salida": 1}
    r = s.post(f"{API}/priorizacion", json=cuerpo, timeout=60)
    print(c, r.status_code, r.text[:160])
    if r.status_code == 200:
        sys.exit("ATENCION: cuerpo aceptado")
