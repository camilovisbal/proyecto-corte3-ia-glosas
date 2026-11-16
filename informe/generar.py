"""Genera informe.html (y el PDF con Edge) llenando la plantilla con calculos.json y los resultados del prototipo."""
import html
import json
import pathlib
import re
import subprocess
import sys

AQUI = pathlib.Path(__file__).parent
RAIZ = AQUI.parent
PROTO = RAIZ / "prototipo"
C = json.loads((RAIZ / "calculos.json").read_text(encoding="utf-8"))
T, K, M, R, P = C["tokens"], C["costos"], C["memoria"], C["roi"], C["parametros"]


def num(x, d=0):
    s = f"{x:,.{d}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def mill(x, d=2):
    return num(x / 1e6, d) + " M"


def cop(x):
    return f"COP {num(x / 1e6, 1)} millones" if x >= 1e7 else f"COP {num(x)}"


def pct(x, d=1):
    return num(100 * x, d) + " %"


V = {}
# --- Cap. 2 ---
V.update(tok_in_mes=mill(T["total_in"]), tok_out_mes=mill(T["total_out"]), factor_pico=num(T["factor_pico"], 1),
         dia_pico_in=mill(T["dia_pico_in"]), dia_pico_out=mill(T["dia_pico_out"]),
         dia_prom_in=mill(T["dia_prom_in"]), dia_prom_out=mill(T["dia_prom_out"]),
         tok_corta=num(T["tokens_corta"]), tok_hosp=num(T["tokens_hosp"]), tok_hist_mes=mill(T["tokens_historia_mes"]),
         tok_hist_en=mill(T["tokens_mes_si_fuera_ingles"]), peq_in=mill(T["peq_in"]), peq_out=mill(T["peq_out"]),
         llm_in=mill(T["llm_in"]), llm_out=mill(T["llm_out"]), llm_hist=num(T["llm_hist"]),
         frac_llm_pct=pct(P["frac_llm"], 0), tps_prom=num(T["tok_s_prom_in"]), tps_pico=num(T["tok_s_pico_in"]),
         api_qwen_usd=num(K["api_qwen_openrouter_usd"], 2), api_qwen_cop=cop(K["api_qwen_openrouter_cop"]),
         api_br_usd=num(K["api_claude_bedrock_usd"], 2), api_br_cop=cop(K["api_claude_bedrock_cop"]),
         g6e_usd=num(K["gpu_alquilada_g6e_usd"], 2), g6e_cop=cop(K["gpu_alquilada_g6e_cop"]),
         amort=cop(K["amortizacion_cop"]), energia=cop(K["energia_cop"]), soporte=cop(K["soporte_cop"]),
         capex_usd=num(K["capex_usd"]), capex_cop=cop(K["capex_cop"]), onprem_mes=cop(K["onprem_mes_cop"]),
         cruce=num(K["cruce_tokens_mes_m"]) + " M",
         cruce_veces=num(K["cruce_tokens_mes_m"] * 1e6 / (T["total_in"] + T["total_out"])),
         tok_hosp_q38=num(T["tokens_hosp_q38"]), tok_hist_q38=mill(T["tokens_historia_mes_q38"]))
prima = K["onprem_mes_cop"] - K["api_qwen_openrouter_cop"]
V["prima"] = cop(prima)
V["prima_pct"] = pct(prima / R["escenarios"]["base"]["neto_mes_cop"])
# --- Cap. 3 ---
m14, m27, cf = M["Qwen3-14B"], M["Qwen3.8-27B"], M["config"]
V.update(ctx_hosp=num(m14["contexto_hosp_tokens"]), ctx_hosp27=num(m27["contexto_hosp_tokens"]),
         m14_bf16=num(m14["pesos_BF16_gb"], 1), m14_int8=num(m14["pesos_INT8_gb"], 1), m14_int4=num(m14["pesos_INT4 (AWQ)_gb"], 1),
         m27_bf16=num(m27["pesos_BF16_gb"], 1), m27_int8=num(m27["pesos_INT8_gb"], 1), m27_int4=num(m27["pesos_INT4 (AWQ)_gb"], 1),
         kv14_fp16=num(m14["kv_hosp_gb"], 2), kv14_fp8=num(m14["kv_hosp_fp8_gb"], 2),
         kv27_fp16=num(m27["kv_hosp_gb"], 2), kv27_fp8=num(m27["kv_hosp_fp8_gb"], 2),
         pesos_total=num(cf["pesos_total_gb"], 1), reserva=num(cf["reserva_gb"], 1), libre_kv=num(cf["libre_kv_gb"], 1),
         sim27=num(cf["hosp_simultaneas_27b_kv_fp8"], 1), sim14=num(cf["hosp_simultaneas_14b_kv_fp8"], 1),
         sim14_fp16=num(cf["hosp_simultaneas_14b"], 1), libre_fp8=num(cf["libre_kv_si_llm_fp8_gb"], 1),
         sim27_fp16=num(cf["hosp_simultaneas_27b"], 1),
         pf14=num(M["prefill_tok_s_14b"]), pf27=num(M["prefill_tok_s_27b"]), horas_gpu_pico=num(M["horas_gpu_dia_pico"], 1))
# --- Cap. 5 ---
b, pe = R["escenarios"]["base"], R["escenarios"]["pesimista"]
V.update(glosa_inicial=cop(R["glosa_inicial_cop"]), perdida_mes=cop(R["perdida_definitiva_cop"]),
         perdida_tarifa=cop(R["perdida_tarifa_cop"]), atacable=cop(R["atacable_ia_cop"]),
         inversion=cop(R["inversion_inicial_cop"]), costo_aud=cop(R["costo_auditores_mes_cop"]),
         ahorro_base=cop(b["ahorro_mes_cop"]), neto_base=cop(b["neto_mes_cop"]), pct_base=pct(b["pct_perdida_total"]),
         meses_base=num(b["meses_recuperacion"], 1),
         ahorro_pes=cop(pe["ahorro_mes_cop"]), neto_pes=cop(pe["neto_mes_cop"]), pct_pes=pct(pe["pct_perdida_total"]),
         meses_pes=num(pe["meses_recuperacion"], 1),
         det_min=pct(R["costo_plataforma_mes_cop"] / (R["atacable_ia_cop"] * P["corrige"])))

# --- Cap. 6 (prototipo) ---
metas = [json.loads(f.read_text()) for f in (PROTO / "datos" / "ocr").glob("*.meta.json")]
V["ocr_seg"] = num(sum(m["segundos"] for m in metas) / len(metas)) if metas else "?"
V["ocr_conf"] = num(sum(m["confianza_media"] for m in metas) / len(metas), 3) if metas else "?"
det = json.loads((PROTO / "salidas" / "detalle.json").read_text(encoding="utf-8"))
tok = json.loads((PROTO / "salidas" / "tokens.json").read_text(encoding="utf-8"))
rev = sum(d["decision"] == "revisar" for d in det)
V["prev_muestra"] = str(rev)
V["prev_pct"] = pct(rev / 300, 0)
V["p_peq"] = str(sum(d["etapa"] != "regla_contrato" for d in det))
V["p_llm"] = str(tok["llm_llamadas"])
V["llm_desc"] = ("Qwen3.8-27B (Groq, nivel gratuito, temperatura 0, sin razonamiento extendido) para las dudosas y para las hospitalizaciones que el modelo pequeño marcó «revisar»; recibe solo las secciones relevantes y devuelve decisión, causa y motivo citado."
                 if tok["llm_llamadas"] else
                 "No se usó LLM en el mejor envío: no hubo historias en la banda gris o no había llave de un proveedor gratuito. Las dudosas se resuelven como «revisar» (decisión conservadora).")
V["enlace_repo"] = "https://github.com/camilovisbal/proyecto-corte3-ia-glosas"


def buscar(o, *claves):
    if isinstance(o, dict):
        for k, v in o.items():
            if k in claves and not isinstance(v, (dict, list)):
                return v
        for v in o.values():
            r = buscar(v, *claves)
            if r is not None:
                return r
    return None


envios = []
log = PROTO / "envios.log"
if log.exists():
    envios = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines() if l.strip()]
validos = [e for e in envios if buscar(e["respuesta"], "f1", "f1_revisar") is not None]
def cel(x):
    return "—" if x is None else html.escape(str(x))


filas = []
for e in envios:
    rr = e["respuesta"]
    filas.append(f"<tr><td class='n'>{e['n']}</td><td>{cel(buscar(rr, 'envio_id'))}</td>"
                 f"<td>{cel(buscar(rr, 'recibido_en'))}</td><td>{cel(buscar(rr, 'codigo_verificacion'))}</td>"
                 f"<td class='n'>{cel(buscar(rr, 'precision', 'precision_revisar'))}</td><td class='n'>{cel(buscar(rr, 'recall', 'recall_revisar'))}</td>"
                 f"<td class='n'>{cel(buscar(rr, 'f1', 'f1_revisar'))}</td><td class='n'>{e['revisar']}</td><td>{html.escape(e.get('cambio', ''))}</td></tr>")
V["tabla_envios"] = ("<p class='nota'>«#» es el número de intento en <code>envios.log</code>. Los intentos con HTTP 422 fueron rechazados por formato antes de calificarse y no cuentan para el límite diario: la propia API informó 4 envíos calificados ese día.</p><table><tr><th>#</th><th>envio_id</th><th>recibido_en</th><th>código</th><th>P</th><th>R</th><th>F1</th>"
                     "<th>revisar</th><th>cambio respecto al anterior</th></tr>" + "".join(filas) + "</table>") if filas else "<p>(pendiente)</p>"
if validos:
    best = max(validos, key=lambda e: (float(buscar(e["respuesta"], "f1", "f1_revisar")), (buscar(e["respuesta"], "tokens_totales") or 0) > 0, e["n"]))
    rr = best["respuesta"]
    V.update(codigo=str(buscar(rr, "codigo_verificacion", "codigo")), envio_id=str(buscar(rr, "envio_id")),
             recibido_en=str(buscar(rr, "recibido_en")), f1=str(buscar(rr, "f1", "f1_revisar")),
             precision=str(buscar(rr, "precision", "precision_revisar")), recall=str(buscar(rr, "recall", "recall_revisar")),
             decl_in=num(best["tokens_entrada"]), decl_out=num(best["tokens_salida"]), n_revisar=str(best["revisar"]),
             captura=best.get("captura", f"{7 + best['n']:02d}-respuesta-envio-{best['n']}.png"))
else:
    for k in ("codigo", "envio_id", "recibido_en", "f1", "precision", "recall", "decl_in", "decl_out", "n_revisar"):
        V[k] = "(pendiente)"
    V["captura"] = "pendiente.png"

# Tokens reales vs estimados
hist = {int(f.stem): json.loads(f.read_text(encoding="utf-8")) for f in (PROTO / "datos" / "historias").glob("*.json")}
sys.path.insert(0, str(PROTO))
from medida import contar_tokens  # noqa: E402
filas_t = []
for tipo, pal_caso, est_ini, est in (("corta", 1500, P["palabras_corta"] * P["tokens_por_palabra_es"], T["tokens_corta"]),
                                     ("hospitalizacion", 15000, P["palabras_hosp"] * P["tokens_por_palabra_es"], T["tokens_hosp"])):
    hs = [h for h in hist.values() if h["tipo"] == tipo and h["texto"]]
    toks = sum(contar_tokens(h["texto"]) for h in hs) / len(hs)
    pal = sum(len(re.findall(r"\w+", h["texto"])) for h in hs) / len(hs)
    escalado = toks / pal * pal_caso
    filas_t.append(f"<tr><td>{tipo}</td><td class='n'>{num(pal)}</td><td class='n'>{num(toks)}</td>"
                   f"<td class='n'>{num(escalado)}</td><td class='n'>{num(est_ini)}</td><td class='n'>{pct(escalado / est_ini - 1)}</td></tr>")
llm_det = [d["llm"] for d in det if d.get("llm")]
llm_in_prom = sum(r["tokens_in"] for r in llm_det) / len(llm_det) if llm_det else 0
llm_out_prom = sum(r["tokens_out"] for r in llm_det) / len(llm_det) if llm_det else 0
V["tabla_tokens"] = (
    "<p>Antes de tener la muestra, el Cap. 2 se iba a estimar con la tasa del corpus paralelo (1,832 tokens/palabra). "
    "Las historias reales de la API, medidas con el mismo tokenizador (Qwen3-14B), salen más caras:</p>"
    "<table><tr><th>Tipo</th><th class='n'>Palabras prom. (API)</th><th class='n'>Tokens prom. reales</th>"
    "<th class='n'>Real escalado a palabras del caso</th><th class='n'>Estimado inicial (×1,832)</th><th class='n'>Diferencia</th></tr>"
    + "".join(filas_t) + "</table>"
    "<p>Por eso el Cap. 2 usa la tasa real (1,985 y 1,900) y no la del corpus: con la inicial, el volumen mensual habría quedado "
    f"subestimado en ≈{pct(T['tokens_historia_mes'] / (63e6 * P['tokens_por_palabra_es']) - 1, 0)}.</p>"
    "<table><tr><th>Llamada</th><th class='n'>Supuesto Cap. 2</th><th class='n'>Real en el prototipo</th><th>Por qué difiere</th></tr>"
    f"<tr><td>Modelo pequeño, entrada por historia</td><td class='n'>texto + 600</td><td class='n'>texto completo ({num(tok['pequeno_in'] / sum(1 for d in det if d.get('tokens')))} prom.)</td>"
    "<td>El prototipo no usa instrucciones (es un modelo estadístico local); en producción Qwen3-14B sí las necesita.</td></tr>"
    f"<tr><td>LLM, entrada por llamada</td><td class='n'>texto completo + 900</td><td class='n'>{num(llm_in_prom)}</td>"
    "<td>El prototipo solo envía las secciones relevantes; en producción el LLM lee la historia completa para citar evidencia de cualquier parte.</td></tr>"
    f"<tr><td>LLM, salida por llamada</td><td class='n'>350</td><td class='n'>{num(llm_out_prom)}</td>"
    "<td>Respuesta en JSON corto. 350 es un supuesto conservador que deja espacio para citar varios fragmentos.</td></tr></table>"
    f"<p>Total declarado en el mejor envío: {num(tok['pequeno_in'] + tok['llm_in'])} tokens de entrada y "
    f"{num(tok['pequeno_out'] + tok['llm_out'])} de salida para 300 historias. Las hospitalizaciones de la API tienen un tercio "
    "de las palabras del caso, así que este total no se extrapola directo: el Cap. 2 parte de las palabras del caso.</p>")
err = AQUI / "errores.html"
V["errores"] = err.read_text(encoding="utf-8") if err.exists() else "<p>(pendiente)</p>"
V["declaracion_ia"] = (AQUI / "declaracion_ia.html").read_text(encoding="utf-8")

plantilla = (AQUI / "plantilla.html").read_text(encoding="utf-8")
faltan = sorted(set(re.findall(r"\[\[(\w+)\]\]", plantilla)) - set(V))
if faltan:
    sys.exit(f"Faltan valores: {faltan}")
salida = re.sub(r"\[\[(\w+)\]\]", lambda m: str(V[m.group(1)]), plantilla)
(AQUI / "informe.html").write_text(salida, encoding="utf-8")
print("informe.html generado")

if "--pdf" in sys.argv:
    edge = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    pdf = AQUI / "Visbal_Camilo_Proyecto_Corte3_IA_glosas.pdf"
    subprocess.run([edge, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={pdf}", (AQUI / "informe.html").as_uri()], timeout=180,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("PDF:", pdf, pdf.exists())
