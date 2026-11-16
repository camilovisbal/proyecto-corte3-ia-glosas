"""Mide el impuesto de tokenizacion del espanol con el tokenizador de Qwen3.

Uso:
  python medir_tokens.py                 -> corpus paralelo ES/EN (textos clinicos ficticios)
  python medir_tokens.py datos/historias  -> tokens/palabra sobre las historias reales de la API

El tokenizador es el oficial de Qwen/Qwen3-32B (identico al de Qwen3-14B),
descargado de huggingface.co el 2026-11-16.
"""
import json
import pathlib
import re
import sys

from tokenizers import Tokenizer

AQUI = pathlib.Path(__file__).parent
TOK = Tokenizer.from_file(str(AQUI / "tokenizador" / "Qwen3-32B-tokenizer.json"))

# Corpus paralelo: frases de nota clinica ficticias, mismo contenido en ambos idiomas.
PARALELO = [
    ("Paciente masculino de 58 años que consulta por dolor torácico opresivo de dos horas de evolución, irradiado al brazo izquierdo, acompañado de diaforesis.",
     "Fifty-eight-year-old male patient presenting with oppressive chest pain of two hours duration, radiating to the left arm, accompanied by diaphoresis."),
    ("Antecedentes de hipertensión arterial en tratamiento con losartán y diabetes mellitus tipo 2 manejada con metformina.",
     "History of arterial hypertension treated with losartan and type 2 diabetes mellitus managed with metformin."),
    ("Al examen físico se encuentra tensión arterial de 160/95, frecuencia cardíaca de 102 latidos por minuto y saturación de oxígeno del 94 por ciento.",
     "Physical examination shows blood pressure of 160/95, heart rate of 102 beats per minute and oxygen saturation of 94 percent."),
    ("Se solicita electrocardiograma, troponina de alta sensibilidad, hemograma completo y radiografía de tórax.",
     "Electrocardiogram, high-sensitivity troponin, complete blood count and chest X-ray are requested."),
    ("El electrocardiograma muestra elevación del segmento ST en derivaciones inferiores; se activa el protocolo de síndrome coronario agudo.",
     "The electrocardiogram shows ST segment elevation in inferior leads; the acute coronary syndrome protocol is activated."),
    ("Se realiza cateterismo cardíaco con implante de stent medicado en la arteria coronaria derecha sin complicaciones.",
     "Cardiac catheterization is performed with implantation of a drug-eluting stent in the right coronary artery without complications."),
    ("Evolución satisfactoria durante la hospitalización; se da egreso al quinto día con indicaciones de rehabilitación cardíaca y control por consulta externa.",
     "Satisfactory progress during hospitalization; discharged on the fifth day with instructions for cardiac rehabilitation and outpatient follow-up."),
    ("Diagnóstico principal: infarto agudo del miocardio de la pared inferior. Diagnósticos relacionados: hipertensión esencial y diabetes tipo 2.",
     "Primary diagnosis: acute myocardial infarction of the inferior wall. Related diagnoses: essential hypertension and type 2 diabetes."),
    ("Paciente femenina de 34 años con cuadro de tres días de fiebre, disuria y dolor lumbar derecho; puño percusión positiva.",
     "Thirty-four-year-old female patient with three days of fever, dysuria and right lumbar pain; positive costovertebral angle tenderness."),
    ("Se inicia antibiótico intravenoso con ceftriaxona y se solicita urocultivo con antibiograma antes de la primera dosis.",
     "Intravenous antibiotic with ceftriaxone is started and a urine culture with susceptibility testing is requested before the first dose."),
    ("La epicrisis y la nota de egreso no se encuentran firmadas por el médico tratante; falta el soporte de la autorización de la EPS.",
     "The discharge summary and discharge note are not signed by the attending physician; the EPS authorization support is missing."),
    ("La auditora revisa la concordancia entre el código diagnóstico registrado en la factura y los hallazgos descritos en la historia clínica.",
     "The auditor reviews the consistency between the diagnostic code recorded on the invoice and the findings described in the medical record."),
]

PALABRA = re.compile(r"\w+", re.UNICODE)


def contar(texto: str) -> tuple[int, int]:
    palabras = len(PALABRA.findall(texto))
    tokens = len(TOK.encode(texto, add_special_tokens=False).ids)
    return palabras, tokens


def paralelo() -> dict:
    pe = te = pi = ti = 0
    for es, en in PARALELO:
        a, b = contar(es)
        c, d = contar(en)
        pe, te, pi, ti = pe + a, te + b, pi + c, ti + d
    return {
        "frases": len(PARALELO),
        "es_palabras": pe, "es_tokens": te, "es_tokens_por_palabra": round(te / pe, 3),
        "en_palabras": pi, "en_tokens": ti, "en_tokens_por_palabra": round(ti / pi, 3),
        "tokens_es_sobre_tokens_en": round(te / ti, 3),
    }


def historias(carpeta: pathlib.Path) -> dict:
    por_tipo: dict[str, list[int]] = {}
    for f in sorted(carpeta.glob("*.json")):
        h = json.loads(f.read_text(encoding="utf-8"))
        texto = h.get("texto") or ""
        if not texto:
            continue
        p, t = contar(texto)
        acc = por_tipo.setdefault(h.get("tipo", "?"), [0, 0, 0])
        acc[0] += 1
        acc[1] += p
        acc[2] += t
    salida = {}
    for tipo, (n, p, t) in por_tipo.items():
        salida[tipo] = {"historias": n, "palabras": p, "tokens": t,
                        "palabras_prom": round(p / n), "tokens_prom": round(t / n),
                        "tokens_por_palabra": round(t / p, 3)}
    return salida


if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(json.dumps(historias(pathlib.Path(sys.argv[1])), indent=2, ensure_ascii=False))
    else:
        print(json.dumps(paralelo(), indent=2, ensure_ascii=False))
