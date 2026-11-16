"""Envia las 300 predicciones juntas a POST /api/clinica/priorizacion con los tokens reales.

Uso:  python enviar.py --confirmo        (sin la bandera solo muestra lo que se enviaria)
Cada envio queda en envios.log (una linea JSON) y la respuesta completa en salidas/respuesta_<n>.json.
"""
import datetime
import json
import sys

from comun import API, AQUI, sesion

SAL = AQUI / "salidas"
preds = json.loads((SAL / "predicciones.json").read_text(encoding="utf-8"))
tok = json.loads((SAL / "tokens.json").read_text(encoding="utf-8"))
assert len(preds) == 300 and len({p["historia_id"] for p in preds}) == 300

# Vocabulario de causas que acepta la API (descubierto con validar_causas.py, sin calificar)
CAUSA_API = {"codigo": "cie10_no_coincide", "soporte": "falta_soporte", "tarifa": "tarifa_contrato"}
tokens_entrada = tok["pequeno_in"] + tok["llm_in"]
tokens_salida = tok["pequeno_out"] + tok["llm_out"]
cuerpo = {
    "predicciones": [dict({"id": p["historia_id"], "riesgo": p["prioridad"], "modelo": p["modelo"],
                           "tokens_entrada": p["tokens"]["pequeno_in"] + p["tokens"]["llm_in"],
                           "tokens_salida": p["tokens"]["pequeno_out"] + p["tokens"]["llm_out"]},
                          **({"causa": CAUSA_API[p["causa"]]} if p["prioridad"] == "revisar" and p["causa"] else {}))
                     for p in preds],
    "tokens_entrada": tokens_entrada,
    "tokens_salida": tokens_salida,
    # Declaracion por modelo (la API resume «modelos» y sus tokens en la metrica)
    "tokens": {"entrada": tokens_entrada, "salida": tokens_salida},
    "modelos": [
        {"nombre": "clasificador-pequeno-local (tokens contados con el tokenizador de Qwen3-14B)",
         "etapa": "modelo_pequeno", "tokens_entrada": tok["pequeno_in"], "tokens_salida": tok["pequeno_out"]},
        {"nombre": "qwen/qwen3.8-27b (Groq)", "etapa": "llm",
         "tokens_entrada": tok["llm_in"], "tokens_salida": tok["llm_out"]},
    ],
}
n_rev = sum(p["prioridad"] == "revisar" for p in preds)
print(f"300 predicciones ({n_rev} revisar), tokens_entrada={tokens_entrada}, tokens_salida={tokens_salida}")
if "--confirmo" not in sys.argv:
    sys.exit("No se envio nada (falta --confirmo).")

r = sesion().post(f"{API}/priorizacion", json=cuerpo, timeout=120)
try:
    resp = r.json()
except ValueError:
    resp = {"texto": r.text[:500]}
log = AQUI / "envios.log"
n = sum(1 for _ in log.open(encoding="utf-8")) + 1 if log.exists() else 1
(SAL / f"respuesta_{n:02d}.json").write_text(json.dumps(resp, ensure_ascii=False, indent=2), encoding="utf-8")
cambio = sys.argv[sys.argv.index("--cambio") + 1] if "--cambio" in sys.argv else ""
linea = {"n": n, "cambio": cambio, "enviado_local": datetime.datetime.now().isoformat(timespec="seconds"), "http": r.status_code,
         "revisar": n_rev, "tokens_entrada": tokens_entrada, "tokens_salida": tokens_salida, "respuesta": resp}
with log.open("a", encoding="utf-8") as f:
    f.write(json.dumps(linea, ensure_ascii=False) + "\n")
print("HTTP", r.status_code)
print(json.dumps(resp, ensure_ascii=False, indent=2))
