"""Etapa 3: LLM grande (Qwen3.8-27B) solo para historias dudosas.

Proveedor del prototipo: Groq (API compatible con OpenAI, modelo qwen/qwen3.8-27b, nivel gratuito).
La llave se lee de %USERPROFILE%\\.clinica_glosas\\groq_key.txt y nunca se imprime.
Sin llave, resolver() devuelve None y la historia queda como dudosa conservadora (revisar).
Los datos son ficticios; en produccion este mismo modelo corre dentro de la clinica (Cap. 4).
"""
import json
import re
import time

import requests

from comun import SECRETOS

URL = "https://api.groq.com/openai/v1/chat/completions"
MODELO = "qwen/qwen3.8-27b"
RUTA_LLAVE = SECRETOS / "groq_key.txt"

SISTEMA = (
    "Eres auditor de cuentas medicas en Colombia. Recibes extractos de una historia clinica y lo que se "
    "facturo. Decide si la factura debe ir a revision humana antes de radicarse. Responde SOLO un JSON: "
    '{"decision":"revisar|bajo","causa":"codigo|soporte|null","motivo":"<max 25 palabras>"}. '
    "codigo = el CIE-10 facturado no corresponde al cuadro descrito o fue descartado. "
    "soporte = un procedimiento facturado no tiene orden, nota o resultado en el expediente. "
    "Si todo concuerda, decision bajo. No inventes datos que no esten en el texto."
)
PARTES = ["motivo de consulta", "enfermedad actual", "examen fisico", "imagenes", "diagnostico",
          "procedimientos y soportes", "facturacion"]


def _llave():
    return RUTA_LLAVE.read_text(encoding="utf-8").strip() if RUTA_LLAVE.exists() else None


def resolver(h, evidencias):
    llave = _llave()
    if not llave:
        return None
    extracto = "\n".join(f"[{p.upper()}]\n{h['sec'].get(p, '').strip()[:1500]}" for p in PARTES)
    usuario = (f"CIE-10 facturado: {h['cie10_facturado']}\nProcedimiento facturado: {h['procedimiento']}\n"
               f"Alertas del clasificador pequeno: {'; '.join(evidencias)[:400]}\n\n{extracto}\n/no_think")
    cuerpo = {"model": MODELO, "temperature": 0, "max_tokens": 120, "reasoning_effort": "none",
              "messages": [{"role": "system", "content": SISTEMA}, {"role": "user", "content": usuario}]}
    for intento in range(6):
        r = requests.post(URL, json=cuerpo, headers={"Authorization": f"Bearer {llave}"}, timeout=90)
        if r.status_code == 429:
            time.sleep(float(r.headers.get("retry-after", 20)) + 1)
            continue
        if r.status_code == 400 and "reasoning_effort" in r.text:
            cuerpo.pop("reasoning_effort", None)
            continue
        r.raise_for_status()
        j = r.json()
        txt = j["choices"][0]["message"]["content"]
        txt = re.sub(r"<think>.*?</think>", "", txt, flags=re.S)
        m = re.search(r"\{.*\}", txt, re.S)
        out = json.loads(m.group(0)) if m else {"decision": "revisar", "causa": None, "motivo": "respuesta no JSON"}
        if out.get("decision") not in ("revisar", "bajo"):
            out["decision"] = "revisar"
        if out.get("causa") in ("null", "", None):
            out["causa"] = None
        u = j.get("usage", {})
        out["tokens_in"] = u.get("prompt_tokens", 0)
        out["tokens_out"] = u.get("completion_tokens", 0)
        time.sleep(2.5)  # respeta el limite de tokens por minuto del nivel gratuito
        return out
    return None
