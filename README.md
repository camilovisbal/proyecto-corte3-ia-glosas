# IA privada contra las glosas — prototipo y cálculos

Proyecto de Aula, Corte 3 · Arquitectura en la Nube (CUC, 2026-2) · Camilo Andrés Visbal Beltrán.
Equipo en la API de la clínica: `visbal-glosas`.

## Contenido

| Ruta | Qué es |
|---|---|
| `calculos.py` → `calculos.json` | Cálculos de tokens, costo, memoria y ROI (capítulos 2, 3 y 5) |
| `medir_tokens.py` | Impuesto del español con el tokenizador oficial de Qwen3 |
| `tokenizador/` | `config.json` de Qwen3-14B y Qwen3.8-27B; los `tokenizer.json` se descargan aparte (ver abajo) |
| `prototipo/` | Flujo del Capítulo 1 contra la API: descarga, OCR, clasificación y envío |
| `diagramas/` | Flujo (Cap. 1) y arquitectura (Cap. 4), en SVG y PNG |
| `capturas/` | Evidencias numeradas (ver `capturas.md`) |
| `informe/` | Plantilla, generador y PDF final |

## Tokenizadores

Los `tokenizer.json` oficiales pesan ~12 MB cada uno y no se versionan. Para medir tokens, descárgalos en `tokenizador/`:

```
curl -L https://huggingface.co/Qwen/Qwen3-32B/resolve/main/tokenizer.json -o tokenizador/Qwen3-32B-tokenizer.json
curl -L https://huggingface.co/Qwen/Qwen3.8-27B/resolve/main/tokenizer.json -o tokenizador/Qwen3.8-27B-tokenizer.json
```

(El tokenizador de Qwen3-32B es idéntico byte a byte al de Qwen3-14B.)

## Cómo correr el prototipo

Requisitos: Python 3.11 o superior.

```
pip install requests tokenizers rapidocr onnxruntime pillow
cd prototipo
python registrar.py        # solo la primera vez; guarda el token en %USERPROFILE%\.clinica_glosas\token.txt
python descargar.py        # 300 historias, 60 imágenes y tarifas en datos/
python ocr.py              # OCR de las 60 escaneadas (CPU; unos 3 min por imagen en un portátil)
python clasificar.py       # regla de contrato + modelo pequeño + LLM para las dudosas
python enviar.py           # muestra lo que enviaría; con --confirmo envía y registra en envios.log
```

Etapa LLM (opcional): si existe `%USERPROFILE%\.clinica_glosas\groq_key.txt`, las historias dudosas se envían a
Qwen3.8-27B (nivel gratuito de Groq) con las secciones relevantes; si no existe, se marcan «revisar».
Con `python clasificar.py --sin-llm` se fuerza el modo sin LLM.

Los secretos (token de la API, llaves) viven fuera de esta carpeta y nunca se imprimen.
Las historias descargadas (`prototipo/datos/`) son ficticias y no se versionan.

## Regenerar el informe

```
python calculos.py
python informe/generar.py --pdf
```
