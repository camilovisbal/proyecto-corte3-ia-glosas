# Requerimientos — Proyecto de Aula Corte 3 (IA privada contra las glosas)

Fuente: https://asur-col.github.io/cuc-arquitectura-nube/proyectos/proyecto-aula-corte3.html (leída el 2026-11-16).
Entrega: PDF único por la tarea de Teams, sábado 28-nov-2026 23:59. Autor único: Camilo Andrés Visbal Beltrán.

## Rúbrica → evidencia

| # | Criterio (peso) | Qué exige «Excelente» (1.0) | Dónde queda la evidencia | Estado |
|---|---|---|---|---|
| 1 | Análisis propio y flujo (Cap. 0 y 1) · 1.0 | ≥4 observaciones propias que cambian el diseño; flujo con OCR, modelo pequeño y grande con criterio, humano al final y % por etapa | Informe §0 (6 observaciones: dato → consecuencia → decisión), §1 + `diagramas/flujo.svg` | pendiente |
| 2 | Tokens, memoria y costo (Cap. 2 y 3) · 1.0 | Cada número rastreable, promedio y pico, entrada y salida separadas | Informe §2–3, `calculos.py` → `calculos.json`, tokenizador Qwen3 medido (`medir_tokens.py`) | pendiente |
| 3 | Despliegue y ley (Cap. 4) · 1.0 | Decisión justificada en costo, operación y ley | Informe §4 + `diagramas/arquitectura.svg`, postura SIC | pendiente |
| 4 | ROI (Cap. 5) · 1.0 | Ahorro atacable bien acotado, supuestos explícitos, escenario pesimista | Informe §5, tabla base/pesimista desde `calculos.py` | pendiente |
| 5 | Prototipo (Cap. 6) · 1.0 | Código de verificación válido; 300 historias con OCR en las 60 escaneadas; F1 «revisar» ≥ 0.70; tokens declarados; análisis de errores | `prototipo/`, `prototipo/envios.log`, captura en `capturas/`, informe §6 | pendiente |

Regla: sin Capítulo 0, el criterio 2 queda en máximo 0.25.

## Requisitos de contenido (checklist)

- [ ] Portada: nombre, cédula, grupo (sin correo).
- [ ] Cap. 0: ≥4 observaciones; cubrir (a) qué no cuadra, (b) pico de fin de mes con historias y tokens, (c) qué no resuelve la IA, (d) riesgos legal/operativo/costo/TI. Cada una: dato exacto, consecuencia, decisión que cambia.
- [ ] Cap. 1: etapas OCR → modelo pequeño (bajo/revisar) → LLM solo dudosas → auditor firma; razonamiento extendido justificado o no usado; diagrama propio con % por etapa y criterio de reparto.
- [ ] Cap. 2: tokens desde palabras; impuesto del español medido con el tokenizador del modelo elegido y fuente declarada; entrada/salida separadas; promedio y pico y cuál dimensiona; API comercial vs GPU propia/alquilada con mismo volumen; fuentes con fecha.
- [ ] Cap. 3: memoria = pesos según cuantización + contexto (KV) por historia; cuantización justificada (pérdida vs. auditoría); familia GPU / instancia AWS / tarjeta; ¿sirven los 2 servidores existentes?
- [ ] Cap. 4: ruta AWS u OpenStack con GPU passthrough; quién opera con 3 personas de TI; diagrama de arquitectura; requisitos SIC aplicables y supuestos; justificar en costo + operación + ley.
- [ ] Cap. 5: ahorro sobre pérdida atacable (no el total), supuestos explícitos, comparación con costo mensual del Cap. 2, meses de recuperación, escenario pesimista (la IA acierta la mitad). Nada de despedir auditores ni eliminar todas las glosas.
- [ ] Cap. 6: equipo registrado una vez; OCR de 60 escaneadas; 300 predicciones en un solo envío con tokens reales; tarifas desde GET /tarifas; mejor resultado con código, envio_id, recibido_en y captura; tokens reales vs. estimados del Cap. 2; ≥2 tipos de error explicados; enlace a carpeta/repositorio; nombre del equipo.
- [ ] Tabla de cálculos (tokens, memoria, costo, ahorro, supuestos, pesimista).
- [ ] Fuentes con fecha de consulta.
- [ ] Declaración de uso de IA.
- [ ] Coherencia: los costos del Cap. 5 son los del Cap. 2; las memorias del Cap. 3 corresponden al modelo del Cap. 2.

## Restricciones del prototipo

- Registro único (`POST /api/clinica/equipos`); token en `%USERPROFILE%\.clinica_glosas\token.txt` (fuera del repo, nunca impreso).
- Máximo 20 envíos/día; cada envío se confirma antes con el autor.
- Cada envío queda en `prototipo/envios.log` (envio_id, recibido_en, código, métricas).
