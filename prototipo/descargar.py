"""Descarga las 300 historias, las imagenes de las escaneadas y las tarifas a datos/."""
import base64
import json

from comun import API, DATOS, sesion

s = sesion()
(DATOS / "historias").mkdir(parents=True, exist_ok=True)
(DATOS / "imagenes").mkdir(parents=True, exist_ok=True)

lista = []
pagina = 1
while True:
    d = s.get(f"{API}/historias", params={"pagina": pagina, "tam": 100}, timeout=60).json()
    lista += d["historias"]
    if pagina >= d["paginas"]:
        break
    pagina += 1
(DATOS / "lista.json").write_text(json.dumps(lista, ensure_ascii=False, indent=1), encoding="utf-8")
(DATOS / "tarifas.json").write_text(json.dumps(s.get(f"{API}/tarifas", timeout=60).json(), ensure_ascii=False, indent=1), encoding="utf-8")

for h in lista:
    hid = h["id"]
    f = DATOS / "historias" / f"{hid:03d}.json"
    if not f.exists():
        f.write_text(json.dumps(s.get(f"{API}/historias/{hid}", timeout=60).json(), ensure_ascii=False, indent=1), encoding="utf-8")
    if h.get("escaneada"):
        destino = list((DATOS / "imagenes").glob(f"{hid:03d}.*"))
        if destino:
            continue
        r = s.get(f"{API}/historias/{hid}/imagen", timeout=120)
        tipo = r.headers.get("content-type", "")
        if tipo.startswith("image/"):
            (DATOS / "imagenes" / f"{hid:03d}.{tipo.split('/')[1].split(';')[0]}").write_bytes(r.content)
        else:  # JSON con la imagen en base64 u otra estructura
            j = r.json()
            (DATOS / "imagenes" / f"{hid:03d}.meta.json").write_text(
                json.dumps({k: (v if not isinstance(v, str) or len(v) < 300 else f"<{len(v)} chars>") for k, v in j.items()}, ensure_ascii=False),
                encoding="utf-8")
            for k, v in j.items():
                if isinstance(v, str) and len(v) > 1000:
                    b64 = v.split(",", 1)[1] if v.startswith("data:") else v
                    ext = "png" if "png" in (j.get("formato", "") + v[:30]) else "img"
                    (DATOS / "imagenes" / f"{hid:03d}.{ext}").write_bytes(base64.b64decode(b64))
print(len(lista), "historias;", sum(h["escaneada"] for h in lista), "escaneadas")
