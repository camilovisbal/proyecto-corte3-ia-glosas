"""Etapa 1 del flujo: OCR de las historias escaneadas con RapidOCR (PP-OCR sobre ONNX Runtime, solo CPU).

Guarda datos/ocr/NNN.txt y datos/ocr/NNN.meta.json (segundos, lineas, confianza media).
Es reanudable: salta las imagenes ya procesadas.
"""
import json
import logging
import time

from rapidocr import RapidOCR

from comun import DATOS

logging.getLogger("RapidOCR").setLevel(logging.WARNING)

salida = DATOS / "ocr"
salida.mkdir(parents=True, exist_ok=True)
motor = RapidOCR()

imagenes = sorted((DATOS / "imagenes").glob("*.png"))
for i, img in enumerate(imagenes, 1):
    hid = img.stem
    if (salida / f"{hid}.txt").exists():
        continue
    t0 = time.time()
    r = motor(str(img))
    seg = time.time() - t0
    lineas = list(r.txts or [])
    conf = [float(s) for s in (r.scores or [])]
    (salida / f"{hid}.txt").write_text("\n".join(lineas), encoding="utf-8")
    (salida / f"{hid}.meta.json").write_text(json.dumps({
        "segundos": round(seg, 1), "lineas": len(lineas),
        "confianza_media": round(sum(conf) / len(conf), 4) if conf else None,
        "confianza_min": round(min(conf), 4) if conf else None,
    }), encoding="utf-8")
    print(f"{i}/{len(imagenes)} {hid} {seg:.0f}s", flush=True)
print("OCR terminado")
