"""Segunda pasada de OCR solo para las escaneadas cuyas lineas clave (diagnostico o soportes) quedaron ilegibles.

Diagnostico del error: la imagen esta limpia, pero el reconocedor comprime las lineas muy anchas
(p. ej. «Se realizo ... con orden medica, nota y resultado anexos al expediente.») y las devuelve ilegibles.
Arreglo: se relee solo la franja superior de la pagina (donde estan diagnostico y soportes), partida en
dos mitades con traslape, para que cada linea sea mas corta; luego se reunen los fragmentos por altura.
Las lineas recuperadas reemplazan a las ilegibles en el texto; queda constancia en NNN.meta.json.
"""
import json
import logging
import time

from PIL import Image
from rapidocr import RapidOCR

import clasificar as c
from comun import DATOS

logging.getLogger("RapidOCR").setLevel(logging.WARNING)
OCR = DATOS / "ocr"
TMP = DATOS / "tmp_reocr.png"
FRANJA = 1600       # px desde arriba: cubre encabezado hasta plan en todas las imagenes de la muestra
TRASLAPE = 60


def lineas_ok(texto):
    dx, sop = c.lineas_clave(c.secciones(texto))
    return bool(c.codigos(dx)), bool(sop)


def leer_mitades(motor, img):
    w = img.width
    partes = []
    for x0, x1 in ((0, w // 2 + TRASLAPE), (w // 2 - TRASLAPE, w)):
        img.crop((x0, 0, x1, min(FRANJA, img.height))).save(TMP)
        r = motor(str(TMP))
        for caja, txt in zip(r.boxes if r.boxes is not None else [], r.txts or []):
            ys = [p[1] for p in caja]
            xs = [p[0] for p in caja]
            partes.append(((min(ys) + max(ys)) / 2, min(xs) + x0, txt))
    partes.sort()
    filas, actual, y_ref = [], [], None
    for y, x, t in partes:
        if y_ref is None or abs(y - y_ref) <= 12:
            actual.append((x, t))
            y_ref = y if y_ref is None else y_ref
        else:
            filas.append(actual)
            actual, y_ref = [(x, t)], y
    if actual:
        filas.append(actual)
    salida = []
    for fila in filas:
        fila.sort()
        texto = ""
        for _, t in fila:  # une los fragmentos quitando la palabra repetida por el traslape
            if texto and t.split() and texto.split()[-1:] == t.split()[:1]:
                t = " ".join(t.split()[1:])
            texto = (texto + " " + t).strip()
        salida.append(texto)
    return "\n".join(salida)


motor = RapidOCR()
for f in sorted(p for p in OCR.glob("*.txt") if ".primera" not in p.name):
    texto = f.read_text(encoding="utf-8")
    dx_ok, sop_ok = lineas_ok(texto)
    meta_prev = json.loads((OCR / f"{f.stem}.meta.json").read_text())
    if (dx_ok and sop_ok) or meta_prev.get("segunda_pasada", {}).get("metodo"):
        continue
    t0 = time.time()
    franja = leer_mitades(motor, Image.open(DATOS / "imagenes" / f"{f.stem}.png").convert("RGB"))
    # se conserva el resto de la pagina (evoluciones) del primer OCR y se antepone la franja releida
    nuevo = franja + "\n" + texto
    n_dx, n_sop = lineas_ok(nuevo)
    meta_f = OCR / f"{f.stem}.meta.json"
    meta = json.loads(meta_f.read_text())
    meta["segunda_pasada"] = {"metodo": "franja superior en dos mitades", "antes": [dx_ok, sop_ok],
                              "despues": [n_dx, n_sop], "segundos": round(time.time() - t0, 1)}
    if (n_dx + n_sop) > (dx_ok + sop_ok):
        (OCR / f"{f.stem}.primera.txt").write_text(texto, encoding="utf-8")
        f.write_text(nuevo, encoding="utf-8")
        meta["segunda_pasada"]["reemplazado"] = True
    meta_f.write_text(json.dumps(meta), encoding="utf-8")
    print(f.stem, meta["segunda_pasada"], flush=True)
TMP.unlink(missing_ok=True)
print("segunda pasada terminada")
