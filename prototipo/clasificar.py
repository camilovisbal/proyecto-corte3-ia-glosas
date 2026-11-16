"""Etapas 2 a 4 del flujo del Capitulo 1 sobre las 300 historias de la API.

  Etapa 2a  Regla de contrato (determinista): valor facturado vs. GET /tarifas.
  Etapa 2b  Modelo pequeno local (CPU): perfil lexico TF-IDF por codigo CIE-10 (centroides)
            + detector de soportes negados + lectura de la seccion DIAGNOSTICO.
            Devuelve bajo / revisar con una confianza; la banda gris va a la etapa 3.
  Etapa 3   LLM (Qwen3-32B, sin razonamiento extendido) solo para las dudosas, con las
            secciones relevantes de la historia. Si no hay llave, la dudosa se resuelve
            con la decision conservadora (revisar) y queda marcada.
  Etapa 4   El auditor firma: el prototipo solo prioriza, no factura.

Salida: salidas/predicciones.json  (300 filas)  y  salidas/detalle.json (evidencia por historia).
"""
import collections
import difflib
import json
import math
import re
import unicodedata

from comun import AQUI, DATOS
import llm

SALIDAS = AQUI / "salidas"
PENDIENTES_BAJO = False  # solo para el envio de calibracion: escaneadas sin OCR aun -> "bajo"
SALIDAS.mkdir(exist_ok=True)

SECCIONES = ["motivo de consulta", "enfermedad actual", "antecedentes", "examen fisico", "laboratorios",
             "imagenes", "diagnostico", "procedimientos y soportes", "plan", "facturacion",
             "signos de alarma", "responsable de la atencion"]
CLINICAS = ["motivo de consulta", "enfermedad actual", "examen fisico", "laboratorios", "imagenes"]
STOP = set("de la el en y a los las del con por para se un una al que su sus no sin es o como mas "
           "paciente quien consulta anos evolucion".split())

NEG_SOPORTE = re.compile(
    r"\bno se anexa|\bsin nota|\bsin que|\bno registra|\bno se encuentra|\bno documenta|\bfalta\b|"
    r"\bausente|\bno hay\b|\bpendiente\b|\bsin soporte|\bsin orden|\bsin resultado|\bsin informe|"
    r"aunque el cargo|aparece facturado sin|\bno se adjunta|\bno consta")
POS_SOPORTE = re.compile(
    r"documentad[oa] con orden|se encuentra complet|anexos? al expediente|con orden medica, nota y resultado")
DX_LINEA = re.compile(r"diagn|impresi.n (clinica|diagnostica)|se descart|explica el cuadro|cuadro compatible|inicialmente anot")
SOP_LINEA = re.compile(r"\b(orden|ordien|resultad|soporte|anex|expediente|autorizaci|informe)")
RAICES_POS = ["orden", "medica", "resultado", "documentado", "anexos", "completo", "expediente", "informe", "historia", "nota"]
DESCARTE = re.compile(r"se descart|no corresponde|diagnostico que explica el cuadro es|"
                      r"inicialmente anotad|cuadro compatible con")


def norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", t or "")
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    return t.replace("—", "-").replace("–", "-")


def secciones(texto: str) -> dict:
    """Corta el texto normalizado por los encabezados conocidos (tolerante al OCR)."""
    lineas = norm(texto).split("\n")
    actual, out = "encabezado", collections.defaultdict(list)
    for l in lineas:
        s = re.sub(r"[^a-z ]", "", l).strip()
        hit = next((h for h in SECCIONES if s == h or (len(s) <= len(h) + 3 and s.startswith(h[:10]))), None)
        if hit:
            actual = hit
        elif re.match(r"(nota de )?evolucion\s*-?\s*dia", s):
            actual = "evolucion"
        else:
            out[actual].append(l)
    return {k: "\n".join(v) for k, v in out.items()}


def codigos(t: str) -> list[str]:
    """Codigos CIE-10 en un texto normalizado; corrige confusiones tipicas del OCR (o->0, l/i->1)."""
    res = []
    for m in re.finditer(r"\b([a-z])\s?(\d|[oil])(\d|[oil])(?:\.(\d{1,3}))?\b", t):
        letra, d1, d2, dec = m.groups()
        fix = lambda c: {"o": "0", "i": "1", "l": "1"}.get(c, c)
        cod = letra.upper() + fix(d1) + fix(d2) + (f".{dec}" if dec else "")
        res.append(cod)
    if not res:
        # El OCR a veces lee la letra inicial como cifra (I10 -> 110, O80 -> 080, S72 -> 572).
        letra_de = {"1": "I", "0": "O", "5": "S", "8": "B"}
        for m in re.finditer(r"(?:[(:]\s*|\s)([1058])(\d)(\d)(?:\.(\d{1,3}))?\b", t):
            l, d1, d2, dec = m.groups()
            res.append(letra_de[l] + d1 + d2 + (f".{dec}" if dec else ""))
    return res


def lineas_clave(sec: dict):
    """Lineas de diagnostico y de soportes buscadas por contenido (no por encabezado), fuera de las
    notas de evolucion: el OCR a veces deja el encabezado una linea por debajo de su contenido."""
    cuerpo = [l for k, v in sec.items() if k not in ("evolucion", "signos de alarma") for l in v.split("\n")]
    dx = [l for l in cuerpo if DX_LINEA.search(l) and "educacion sobre" not in l]
    sop = [l for l in cuerpo if SOP_LINEA.search(l) and not DX_LINEA.search(l) and len(l) > 25]
    return "\n".join(dx), sop


def soporte_positivo(l: str) -> bool:
    """Frase de soporte completo, tolerante a errores de OCR (similitud aproximada de palabras)."""
    if POS_SOPORTE.search(l):
        return True
    hits = {difflib.get_close_matches(w, RAICES_POS, n=1, cutoff=0.75)[0]
            for w in re.findall(r"[a-z]{4,}", l) if difflib.get_close_matches(w, RAICES_POS, n=1, cutoff=0.75)}
    return len(hits) >= 3


def tokens_lex(t: str) -> list[str]:
    return [w for w in re.findall(r"[a-z]{3,}", t) if w not in STOP]


def cargar():
    tar = json.loads((DATOS / "tarifas.json").read_text(encoding="utf-8"))["eps"]
    hist = []
    for f in sorted((DATOS / "historias").glob("*.json")):
        h = json.loads(f.read_text(encoding="utf-8"))
        if h["escaneada"]:
            o = DATOS / "ocr" / f"{h['id']:03d}.txt"
            h["texto_modelo"] = o.read_text(encoding="utf-8") if o.exists() else ""
            m = DATOS / "ocr" / f"{h['id']:03d}.meta.json"
            h["ocr"] = json.loads(m.read_text()) if m.exists() else None
        else:
            h["texto_modelo"] = h["texto"]
        h["sec"] = secciones(h["texto_modelo"])
        hist.append(h)
    return hist, tar


def centroides(hist):
    """Perfil TF-IDF del cuadro clinico por codigo facturado (aprendido sin etiquetas: la mayoria
    de historias de cada codigo son coherentes, asi que el centroide representa el cuadro tipico)."""
    docs = {h["id"]: collections.Counter(tokens_lex(" ".join(h["sec"].get(s, "") for s in CLINICAS))) for h in hist}
    df = collections.Counter(w for d in docs.values() for w in d)
    n = len(docs)
    idf = {w: math.log(n / (1 + c)) + 1 for w, c in df.items()}

    def vec(c):
        v = {w: (1 + math.log(f)) * idf.get(w, 1) for w, f in c.items()}
        z = math.sqrt(sum(x * x for x in v.values())) or 1
        return {w: x / z for w, x in v.items()}

    vecs = {i: vec(c) for i, c in docs.items()}
    por_cod = collections.defaultdict(list)
    for h in hist:
        por_cod[h["cie10_facturado"]].append(vecs[h["id"]])
    cent = {}
    for cod, vs in por_cod.items():
        acc = collections.Counter()
        for v in vs:
            acc.update(v)
        z = math.sqrt(sum(x * x for x in acc.values())) or 1
        cent[cod] = {w: x / z for w, x in acc.items()}
    return vecs, cent


def cos(a, b):
    if len(a) > len(b):
        a, b = b, a
    return sum(x * b.get(w, 0) for w, x in a.items())


def modelo_pequeno(h, vec, cent):
    """Devuelve (decision, causa, confianza 0..1, evidencias)."""
    ev = []
    fact = h["cie10_facturado"]
    dx, lineas_sop = lineas_clave(h["sec"])
    if not h["texto_modelo"].strip():
        if PENDIENTES_BAJO:
            return "bajo", None, 0.5, ["sin OCR todavia (envio de calibracion)"]
        return "revisar", "soporte", 0.5, ["sin texto legible"]

    # (a) Seccion DIAGNOSTICO: codigo facturado ausente o descartado explicitamente
    cods_dx = codigos(dx)
    s_cod = 0.0
    if DESCARTE.search(dx):
        s_cod += 0.6
        ev.append("diagnostico: lenguaje de descarte/cambio")
    if cods_dx and fact not in cods_dx:
        s_cod += 0.5
        ev.append(f"diagnostico cita {cods_dx} y se facturo {fact}")
    elif not cods_dx:
        s_cod += 0.15
        ev.append("diagnostico sin codigo legible")

    # (b) Cuadro clinico vs. perfil del codigo facturado
    sims = sorted(((cos(vec, c), k) for k, c in cent.items()), reverse=True)
    sim_fact = next(s for s, k in sims if k == fact) if fact in cent else 0
    mejor_s, mejor_k = sims[0]
    if mejor_k != fact and mejor_s - sim_fact > 0.05:
        s_cod += min(0.6, 2 * (mejor_s - sim_fact))
        ev.append(f"cuadro clinico se parece mas a {mejor_k} ({mejor_s:.2f}) que a {fact} ({sim_fact:.2f})")

    # (c) Soportes
    s_sop = 0.0
    if not lineas_sop:
        s_sop = 0.35
        ev.append("seccion de soportes vacia o ilegible")
    for l in lineas_sop:
        if NEG_SOPORTE.search(l):
            s_sop = max(s_sop, 0.9)
            ev.append("soporte: " + l.strip()[:120])
        elif not soporte_positivo(l):
            s_sop = max(s_sop, 0.4)
            ev.append("soporte con redaccion no reconocida: " + l.strip()[:120])

    s = max(s_cod, s_sop)
    causa = "codigo" if s_cod >= s_sop else "soporte"
    if s >= 0.6:
        return "revisar", causa, min(1.0, 0.5 + s / 2), ev
    if s <= 0.2:
        return "bajo", None, 1 - s, ev
    return "dudosa", causa, 0.5, ev


def main(usar_llm=True):
    hist, tar = cargar()
    vecs, cent = centroides(hist)
    preds, detalle = [], []
    tok = {"pequeno_in": 0, "pequeno_out": 0, "llm_in": 0, "llm_out": 0, "llm_llamadas": 0}
    from medida import contar_tokens
    for h in hist:
        hid = h["id"]
        d = {"historia_id": hid, "tipo": h["tipo"], "escaneada": h["escaneada"]}
        # Etapa 2a: regla de contrato
        t = tar.get(h["eps"], {}).get(h["procedimiento"])
        if t is None or h["valor_cop"] != t["valor_cop"]:
            d.update(decision="revisar", causa="tarifa", etapa="regla_contrato",
                     evidencia=[f"facturado {h['valor_cop']} vs contrato {t and t['valor_cop']}"])
        else:
            # Etapa 2b: el modelo pequeno lee la historia completa
            t_in = contar_tokens(h["texto_modelo"])
            tok["pequeno_in"] += t_in
            d["tokens"] = {"pequeno_in": t_in, "pequeno_out": 12, "llm_in": 0, "llm_out": 0}
            dec, causa, conf, ev = modelo_pequeno(h, vecs[hid], cent)
            tok["pequeno_out"] += 12  # salida estructurada equivalente: {"r":"bajo|revisar","c":"..."}
            d.update(decision=dec, causa=causa, confianza=round(conf, 2), etapa="modelo_pequeno", evidencia=ev)
            if dec == "revisar" and h["tipo"] == "hospitalizacion" and usar_llm:
                # Hospitalizacion en riesgo: el LLM aporta la cita para el auditor; la prioridad no baja.
                r = llm.resolver(h, ev)
                if r:
                    d.update(etapa="modelo_pequeno+llm_cita", llm=r)
                    d["tokens"].update(llm_in=r["tokens_in"], llm_out=r["tokens_out"])
                    tok["llm_in"] += r["tokens_in"]
                    tok["llm_out"] += r["tokens_out"]
                    tok["llm_llamadas"] += 1
            if dec == "dudosa":
                r = llm.resolver(h, ev) if usar_llm else None
                if r:
                    d.update(decision=r["decision"], causa=r.get("causa"), etapa="llm", llm=r)
                    d["tokens"].update(llm_in=r["tokens_in"], llm_out=r["tokens_out"])
                    tok["llm_in"] += r["tokens_in"]
                    tok["llm_out"] += r["tokens_out"]
                    tok["llm_llamadas"] += 1
                else:
                    d.update(decision="revisar", etapa="dudosa_conservadora")
        detalle.append(d)
        tk = d.get("tokens", {"pequeno_in": 0, "pequeno_out": 0, "llm_in": 0, "llm_out": 0})
        preds.append({"historia_id": hid, "prioridad": d["decision"], "tokens": tk,
                      "modelo": "qwen/qwen3.8-27b" if tk["llm_in"] else ("clasificador-pequeno-local" if tk["pequeno_in"] else "regla-contrato"),
                      "causa": d.get("causa") if d["decision"] == "revisar" else None})
    (SALIDAS / "predicciones.json").write_text(json.dumps(preds, ensure_ascii=False, indent=1), encoding="utf-8")
    (SALIDAS / "detalle.json").write_text(json.dumps(detalle, ensure_ascii=False, indent=1), encoding="utf-8")
    (SALIDAS / "tokens.json").write_text(json.dumps(tok, indent=1), encoding="utf-8")
    c = collections.Counter((d["decision"], d.get("causa"), d["etapa"]) for d in detalle)
    for k, v in sorted(c.items(), key=lambda x: -x[1]):
        print(v, k)
    print("tokens", tok)


if __name__ == "__main__":
    import sys
    PENDIENTES_BAJO = "--pendientes-bajo" in sys.argv
    main(usar_llm="--sin-llm" not in sys.argv)
