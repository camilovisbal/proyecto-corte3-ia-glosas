"""Calculos de los capitulos 2 (tokens y costo), 3 (memoria) y 5 (ROI).

Cada parametro lleva su origen:
  [S2]  dato de la seccion 2 del enunciado
  [MED] medido por el autor (script y fecha indicados)
  [F]   fuente externa con fecha de consulta (ver FUENTES)
  [SUP] supuesto del autor, declarado en el informe
Ejecutar:  python calculos.py   -> imprime tablas y escribe calculos.json
"""
import json
import pathlib

P = {
    # ---- Datos del caso [S2] ----
    "facturacion_mes_cop": 18_000e6,
    "atenciones_cortas": 12_000,
    "atenciones_hosp": 3_000,
    "palabras_corta": 1_500,
    "palabras_hosp": 15_000,
    "glosa_inicial": 0.10,
    "glosa_definitiva": 0.04,
    "causa_codigo": 0.45,
    "causa_soporte": 0.30,
    "causa_tarifa": 0.25,
    "auditores": 6,
    "costo_auditor_cop": 6e6,
    "historias_dia_auditor": 120,
    "fraccion_pico": 0.60,
    "dias_pico": 5,
    "fraccion_escaneada": 0.20,
    # ---- Medidos [MED] ----
    "tokens_por_palabra_es": 1.832,      # medir_tokens.py, corpus paralelo ES, Qwen3, 2026-11-16
    "tokens_por_palabra_en": 1.373,      # mismo corpus en ingles
    "tpp_corta": 1.985,                  # medir_tokens.py sobre 180 historias cortas de la API
    "tpp_hosp": 1.900,                   # medir_tokens.py sobre 60 hospitalizaciones de la API
    # mismo procedimiento con el tokenizador de Qwen3.8-27B (LLM), 2026-11-16
    "tpp_es_q38": 1.591, "tpp_en_q38": 1.368,
    "tpp_corta_q38": 1.811,
    "tpp_hosp_q38": 1.723,
    # ---- Supuestos de calendario [SUP] ----
    "dias_mes": 30,
    "dias_habiles": 22,
    "horas_operacion_pico": 24,          # la cola corre dia y noche en el pico
    # ---- Reparto del flujo [SUP, Cap. 1] ----
    "frac_llm": 0.20,                    # dudosas (banda gris) + hospitalizaciones marcadas revisar
    "frac_revisar": 0.15,                # marcadas revisar: ~10 % real (muestra API) + falsos positivos
    "frac_muestra_bajo": 0.05,           # control de calidad sobre lo marcado como bajo
    # ---- Tokens fijos por llamada [SUP; se contrasta con el prototipo en Cap. 6] ----
    "prompt_pequeno": 600,
    "salida_pequeno": 60,
    "prompt_llm": 900,
    "salida_llm": 350,
    # ---- Precios [F] ----
    "trm": 3_300,                        # COP/USD, TRM 3.297,07 del 2026-11-11 redondeada
    "or_q14_in": 0.12, "or_q14_out": 0.24,   # OpenRouter qwen/qwen3-14b, USD/M, 2026-11-16
    "or_q38_in": 0.15, "or_q38_out": 1.875,  # OpenRouter qwen/qwen3.8-27b, USD/M, 2026-11-16
    "br_haiku_in": 0.10, "br_haiku_out": 0.50,    # Bedrock Claude Haiku 5.5 (material S15, 2026-11-05)
    "br_sonnet_in": 2.00, "br_sonnet_out": 10.00, # Bedrock Claude Sonnet 5.5 (material S15, 2026-11-05)
    "g6e_hora": 1.861,                   # g6e.xlarge (1x L40S 48 GB) us-east-1 on-demand, 2026-11-16
    "horas_mes": 730,
    "l40s_usd": 6_799,                   # nueva, Amazon EE. UU., gpudojo.com/l40s 2026-11-16
    "servidor_base_usd": 9_000,          # [SUP] chasis 2U certificado GPU, 2 CPU, 256 GB RAM, discos
    "amortizacion_meses": 36,            # [SUP]
    "kw_promedio": 0.9,                  # [SUP] servidor GPU con carga media
    "cop_kwh": 1_000,                    # [SUP] tarifa comercial Barranquilla
    "soporte_integrador_cop": 10e6,      # [SUP] contrato mensual OpenStack+vLLM nivel 2-3
    "implementacion_cop": 60e6,          # [SUP] unica vez: instalacion, integracion, capacitacion
    "segundo_isp_cop": 0,                # ruta on-prem: no es critico (ver Cap. 4)
    # ---- Hardware [F] ----
    "vram_l40s_gb": 48,
    "tflops_l40s_fp16": 362,             # densos, hoja de datos NVIDIA L40S
    "mfu": 0.35,                         # [SUP] utilizacion efectiva en prefill
    # ---- ROI [SUP] ----
    "detecta_base": 0.60,                # la IA detecta el 60 % de errores de codigo y soporte
    "corrige": 0.70,                     # de lo detectado, el auditor logra corregir el 70 % antes de radicar
}

MODELOS = {
    # params en miles de millones; arquitectura de config.json oficial (huggingface.co/Qwen, 2026-11-16)
    # capas_kv = capas con atencion completa (las unicas que guardan cache KV que crece con el contexto)
    "Qwen3-14B": {"params_b": 14.8, "capas_kv": 40, "kv_heads": 8, "head_dim": 128, "estado_fijo_gb": 0.0},
    # Qwen3.8-27B: 64 capas, 1 de cada 4 con atencion completa (16); las 48 lineales guardan un estado fijo
    # por secuencia: 48 capas x 48 cabezas x 128 x 128 x 4 bytes (fp32) = 0,151 GB
    "Qwen3.8-27B": {"params_b": 27.8, "capas_kv": 16, "kv_heads": 4, "head_dim": 256,
                    "estado_fijo_gb": 48 * 48 * 128 * 128 * 4 / 1e9},
}
BYTES = {"BF16": 2.0, "INT8": 1.0, "INT4 (AWQ)": 0.5}
SOBRECARGA_CUANT = 1.10   # [SUP] escalas/ceros de la cuantizacion y capas no cuantizadas (embeddings)


def tokens():
    n = P["atenciones_cortas"] + P["atenciones_hosp"]
    palabras = P["atenciones_cortas"] * P["palabras_corta"] + P["atenciones_hosp"] * P["palabras_hosp"]
    tok_hist = (P["atenciones_cortas"] * P["palabras_corta"] * P["tpp_corta"]
                + P["atenciones_hosp"] * P["palabras_hosp"] * P["tpp_hosp"])
    t = {
        "historias_mes": n,
        "palabras_mes": palabras,
        "palabras_hosp_frac": P["atenciones_hosp"] * P["palabras_hosp"] / palabras,
        "tokens_corta": P["palabras_corta"] * P["tpp_corta"],
        "tokens_hosp": P["palabras_hosp"] * P["tpp_hosp"],
        "impuesto_es_en": P["tokens_por_palabra_es"] / P["tokens_por_palabra_en"],
        "tokens_historia_mes": tok_hist,
        "tokens_mes_si_fuera_ingles": tok_hist / (P["tokens_por_palabra_es"] / P["tokens_por_palabra_en"]),
    }
    # Modelo pequeno: lee todas
    t["peq_in"] = tok_hist + n * P["prompt_pequeno"]
    t["peq_out"] = n * P["salida_pequeno"]
    # LLM: solo dudosas (fraccion uniforme sobre cortas y hospitalizaciones), con su propio tokenizador
    tok_hist_q38 = (P["atenciones_cortas"] * P["palabras_corta"] * P["tpp_corta_q38"]
                    + P["atenciones_hosp"] * P["palabras_hosp"] * P["tpp_hosp_q38"])
    t["tokens_corta_q38"] = P["palabras_corta"] * P["tpp_corta_q38"]
    t["tokens_hosp_q38"] = P["palabras_hosp"] * P["tpp_hosp_q38"]
    t["tokens_historia_mes_q38"] = tok_hist_q38
    t["impuesto_es_en_q38"] = P["tpp_es_q38"] / P["tpp_en_q38"]
    t["llm_hist"] = n * P["frac_llm"]
    t["llm_in"] = tok_hist_q38 * P["frac_llm"] + t["llm_hist"] * P["prompt_llm"]
    t["llm_out"] = t["llm_hist"] * P["salida_llm"]
    t["total_in"] = t["peq_in"] + t["llm_in"]
    t["total_out"] = t["peq_out"] + t["llm_out"]
    # Promedio diario vs pico
    f_dia_pico = P["fraccion_pico"] / P["dias_pico"]
    f_dia_prom = 1 / P["dias_mes"]
    t["factor_pico"] = f_dia_pico / f_dia_prom
    for k in ("in", "out"):
        tot = t[f"total_{k}"]
        t[f"dia_prom_{k}"] = tot * f_dia_prom
        t[f"dia_pico_{k}"] = tot * f_dia_pico
    t["hist_dia_prom"] = n * f_dia_prom
    t["hist_dia_pico"] = n * f_dia_pico
    t["hist_pico_5dias"] = n * P["fraccion_pico"]
    t["tok_s_pico_in"] = t["dia_pico_in"] / (P["horas_operacion_pico"] * 3600)
    t["tok_s_pico_out"] = t["dia_pico_out"] / (P["horas_operacion_pico"] * 3600)
    t["tok_s_prom_in"] = t["dia_prom_in"] / 86400
    # Escaneadas y paginas (500 palabras por pagina [SUP])
    t["escaneadas_mes"] = n * P["fraccion_escaneada"]
    t["paginas_ocr_mes"] = (P["atenciones_cortas"] * P["palabras_corta"] + P["atenciones_hosp"] * P["palabras_hosp"]) * P["fraccion_escaneada"] / 500
    return t


def costos(t):
    M = 1e6
    c = {}
    c["api_qwen_openrouter_usd"] = (t["peq_in"] / M * P["or_q14_in"] + t["peq_out"] / M * P["or_q14_out"]
                                   + t["llm_in"] / M * P["or_q38_in"] + t["llm_out"] / M * P["or_q38_out"])
    c["api_claude_bedrock_usd"] = (t["peq_in"] / M * P["br_haiku_in"] + t["peq_out"] / M * P["br_haiku_out"]
                                  + t["llm_in"] / M * P["br_sonnet_in"] + t["llm_out"] / M * P["br_sonnet_out"])
    c["gpu_alquilada_g6e_usd"] = P["g6e_hora"] * P["horas_mes"]
    capex_usd = P["l40s_usd"] + P["servidor_base_usd"]
    c["capex_usd"] = capex_usd
    c["capex_cop"] = capex_usd * P["trm"]
    c["amortizacion_cop"] = c["capex_cop"] / P["amortizacion_meses"]
    c["energia_cop"] = P["kw_promedio"] * P["horas_mes"] * P["cop_kwh"]
    c["soporte_cop"] = P["soporte_integrador_cop"]
    c["onprem_mes_cop"] = c["amortizacion_cop"] + c["energia_cop"] + c["soporte_cop"]
    c["onprem_mes_sin_soporte_cop"] = c["amortizacion_cop"] + c["energia_cop"]
    for k in ("api_qwen_openrouter", "api_claude_bedrock", "gpu_alquilada_g6e"):
        c[f"{k}_cop"] = c[f"{k}_usd"] * P["trm"]
    # Punto de cruce: tokens/mes a los que la API Qwen iguala el costo on-prem sin soporte
    costo_mezcla_por_m = c["api_qwen_openrouter_usd"] / ((t["total_in"] + t["total_out"]) / M)
    c["usd_por_m_tokens_mezcla_qwen"] = costo_mezcla_por_m
    c["cruce_tokens_mes_m"] = (c["onprem_mes_sin_soporte_cop"] / P["trm"]) / costo_mezcla_por_m
    return c


def memoria(t):
    out = {}
    ctxs = {"Qwen3-14B": t["tokens_hosp"] + P["prompt_pequeno"] + P["salida_pequeno"],
            "Qwen3.8-27B": t["tokens_hosp_q38"] + P["prompt_llm"] + P["salida_llm"]}
    for nombre, m in MODELOS.items():
        kv_por_token = 2 * m["capas_kv"] * m["kv_heads"] * m["head_dim"] * 2  # K y V, FP16
        ctx = ctxs[nombre]
        fila = {"kv_bytes_por_token": kv_por_token,
                "contexto_hosp_tokens": ctx,
                "estado_fijo_gb": m["estado_fijo_gb"],
                "kv_hosp_gb": kv_por_token * ctx / 1e9 + m["estado_fijo_gb"],
                "kv_hosp_fp8_gb": kv_por_token / 2 * ctx / 1e9 + m["estado_fijo_gb"]}
        for q, b in BYTES.items():
            pesos = m["params_b"] * b * (SOBRECARGA_CUANT if b < 2 else 1.0)
            fila[f"pesos_{q}_gb"] = pesos
        out[nombre] = fila
    # Configuracion elegida: ambos INT4 en una L40S de 48 GB
    peso_14 = out["Qwen3-14B"]["pesos_INT4 (AWQ)_gb"]
    peso_27 = out["Qwen3.8-27B"]["pesos_INT4 (AWQ)_gb"]
    reserva = 0.10 * P["vram_l40s_gb"]  # [SUP] activaciones, grafos CUDA, fragmentacion
    libre_kv = P["vram_l40s_gb"] - peso_14 - peso_27 - reserva
    out["config"] = {
        "pesos_total_gb": peso_14 + peso_27,
        "reserva_gb": reserva,
        "libre_kv_gb": libre_kv,
        "hosp_simultaneas_27b": libre_kv / 2 / out["Qwen3.8-27B"]["kv_hosp_gb"],
        "hosp_simultaneas_14b": libre_kv / 2 / out["Qwen3-14B"]["kv_hosp_gb"],
        # con cache KV en FP8 (1 byte): vLLM --kv-cache-dtype fp8
        "hosp_simultaneas_27b_kv_fp8": libre_kv / 2 / out["Qwen3.8-27B"]["kv_hosp_fp8_gb"],
        "hosp_simultaneas_14b_kv_fp8": libre_kv / 2 / out["Qwen3-14B"]["kv_hosp_fp8_gb"],
        # alternativa: LLM en FP8 oficial (Qwen/Qwen3.8-27B-FP8)
        "libre_kv_si_llm_fp8_gb": P["vram_l40s_gb"] - peso_14 - out["Qwen3.8-27B"]["pesos_INT8_gb"] - reserva,
    }
    # Rendimiento de prefill estimado (2 FLOP por parametro por token)
    ef = P["tflops_l40s_fp16"] * 1e12 * P["mfu"]
    out["prefill_tok_s_14b"] = ef / (2 * MODELOS["Qwen3-14B"]["params_b"] * 1e9)
    out["prefill_tok_s_27b"] = ef / (2 * MODELOS["Qwen3.8-27B"]["params_b"] * 1e9)
    # Horas de GPU que pide el dia pico (prefill domina)
    peq_pico = t["peq_in"] * P["fraccion_pico"] / P["dias_pico"]
    llm_pico = t["llm_in"] * P["fraccion_pico"] / P["dias_pico"]
    out["horas_gpu_dia_pico"] = (peq_pico / out["prefill_tok_s_14b"] + llm_pico / out["prefill_tok_s_27b"]) / 3600
    return out


def roi(c):
    perdida = P["facturacion_mes_cop"] * P["glosa_definitiva"]
    atacable = perdida * (P["causa_codigo"] + P["causa_soporte"])
    costo_mes = c["onprem_mes_cop"]
    inversion = c["capex_cop"] + P["implementacion_cop"]
    esc = {}
    for nombre, det in (("base", P["detecta_base"]), ("pesimista", P["detecta_base"] / 2)):
        ahorro = atacable * det * P["corrige"]
        neto = ahorro - costo_mes
        esc[nombre] = {"detecta": det, "ahorro_mes_cop": ahorro, "neto_mes_cop": neto,
                       "meses_recuperacion": inversion / neto if neto > 0 else None,
                       "pct_perdida_total": ahorro / perdida}
    return {"glosa_inicial_cop": P["facturacion_mes_cop"] * P["glosa_inicial"],
            "perdida_definitiva_cop": perdida, "perdida_tarifa_cop": perdida * P["causa_tarifa"],
            "atacable_ia_cop": atacable, "costo_plataforma_mes_cop": costo_mes,
            "inversion_inicial_cop": inversion, "costo_auditores_mes_cop": P["auditores"] * P["costo_auditor_cop"],
            "escenarios": esc}


def auditores(t):
    cap_dia = P["auditores"] * P["historias_dia_auditor"]
    palabras_dia_aud = t["palabras_mes"] / (P["auditores"] * P["dias_habiles"])
    revisar_pico_dia = t["hist_dia_pico"] * (P["frac_revisar"] + P["frac_muestra_bajo"])
    return {"capacidad_dia": cap_dia, "capacidad_mes": cap_dia * P["dias_habiles"],
            "palabras_dia_por_auditor": palabras_dia_aud,
            "horas_lectura_dia_por_auditor_250ppm": palabras_dia_aud / 250 / 60,
            "minutos_lectura_hosp_250ppm": P["palabras_hosp"] / 250,
            "pico_hoy_dia": t["hist_dia_pico"], "pico_con_ia_dia": revisar_pico_dia,
            "sobrecarga_hoy": t["hist_dia_pico"] / cap_dia, "carga_con_ia": revisar_pico_dia / cap_dia}


if __name__ == "__main__":
    T = tokens()
    C = costos(T)
    MEM = memoria(T)
    R = roi(C)
    A = auditores(T)
    res = {"parametros": P, "tokens": T, "costos": C, "memoria": MEM, "roi": R, "auditores": A}
    pathlib.Path(__file__).with_name("calculos.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")

    def m(x):
        return f"{x/1e6:,.2f} M"
    print("== Tokens ==")
    print(f"palabras/mes {T['palabras_mes']:,.0f}  (hosp {T['palabras_hosp_frac']:.1%})")
    print(f"tokens historia: corta {T['tokens_corta']:,.0f}  hosp {T['tokens_hosp']:,.0f}  total/mes {m(T['tokens_historia_mes'])} (si fuera ingles {m(T['tokens_mes_si_fuera_ingles'])})")
    print(f"pequeno in {m(T['peq_in'])} out {m(T['peq_out'])} | LLM ({T['llm_hist']:,.0f} hist) in {m(T['llm_in'])} out {m(T['llm_out'])}")
    print(f"TOTAL in {m(T['total_in'])} out {m(T['total_out'])}")
    print(f"dia promedio in {m(T['dia_prom_in'])} out {m(T['dia_prom_out'])} | dia pico in {m(T['dia_pico_in'])} out {m(T['dia_pico_out'])}  factor {T['factor_pico']:.2f}")
    print(f"historias: dia prom {T['hist_dia_prom']:.0f}, dia pico {T['hist_dia_pico']:.0f}, 5 dias pico {T['hist_pico_5dias']:.0f}")
    print(f"tok/s pico (24h) in {T['tok_s_pico_in']:.0f} out {T['tok_s_pico_out']:.1f}; promedio in {T['tok_s_prom_in']:.0f}")
    print(f"escaneadas/mes {T['escaneadas_mes']:.0f}, paginas OCR/mes {T['paginas_ocr_mes']:,.0f}")
    print("== Costos/mes ==")
    for k in ("api_qwen_openrouter", "api_claude_bedrock", "gpu_alquilada_g6e"):
        print(f"{k}: USD {C[k+'_usd']:,.2f}  COP {C[k+'_cop']:,.0f}")
    print(f"on-prem: capex USD {C['capex_usd']:,} (COP {C['capex_cop']:,.0f}); amort {C['amortizacion_cop']:,.0f} energia {C['energia_cop']:,.0f} soporte {C['soporte_cop']:,.0f} => {C['onprem_mes_cop']:,.0f}")
    print(f"mezcla Qwen API USD/M {C['usd_por_m_tokens_mezcla_qwen']:.4f}; cruce on-prem(sin soporte) {C['cruce_tokens_mes_m']:,.0f} M tokens/mes")
    print("== Memoria ==")
    for k, v in MEM.items():
        print(k, json.dumps(v, ensure_ascii=False) if isinstance(v, dict) else round(v, 2))
    print("== ROI ==")
    print(json.dumps(R, indent=1, ensure_ascii=False))
    print("== Auditores ==")
    print(json.dumps(A, indent=1))
