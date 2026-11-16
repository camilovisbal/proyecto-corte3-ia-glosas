"""Convierte la respuesta de un envio (salidas/respuesta_NN.json) en una captura PNG en ../capturas/.

Uso: python captura_respuesta.py NN
La pagina muestra el endpoint, el equipo y el JSON tal como lo devolvio la API (sin token).
"""
import html
import json
import subprocess
import sys

from comun import AQUI

n = int(sys.argv[1])
resp = json.loads((AQUI / "salidas" / f"respuesta_{n:02d}.json").read_text(encoding="utf-8"))
texto = json.dumps(resp, ensure_ascii=False, indent=2)
assert "Bearer" not in texto
pagina = AQUI / "salidas" / f"respuesta_{n:02d}.html"
pagina.write_text(f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><style>
body{{font-family:Segoe UI,Arial,sans-serif;margin:24px;background:#fff;color:#111}}
.t{{font-size:18px;font-weight:600;margin-bottom:6px}} .s{{color:#444;font-size:14px;margin-bottom:14px}}
pre{{background:#f4f4f4;border:1px solid #ccc;padding:16px;font-size:15px;line-height:1.45;white-space:pre-wrap}}
</style></head><body>
<div class="t">POST https://labs.proyectoasur.org/api/clinica/priorizacion → respuesta del envío {n}</div>
<div class="s">Equipo: visbal-glosas (equipo_id 7) · 300 predicciones · Authorization: Bearer &lt;oculto&gt;</div>
<pre>{html.escape(texto)}</pre></body></html>""", encoding="utf-8")
destino = AQUI.parent / "capturas" / f"{7 + n:02d}-respuesta-envio-{n}.png"
edge = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
p = subprocess.Popen([edge, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--window-size=1000,900",
                      f"--screenshot={destino}", pagina.as_uri()], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    p.wait(timeout=60)
except subprocess.TimeoutExpired:
    p.kill()
print(destino.name, destino.exists())
