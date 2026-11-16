"""Constantes y cliente HTTP compartidos por el prototipo."""
import pathlib

import requests

API = "https://labs.proyectoasur.org/api/clinica"
SECRETOS = pathlib.Path.home() / ".clinica_glosas"
RUTA_TOKEN = SECRETOS / "token.txt"
AQUI = pathlib.Path(__file__).parent
DATOS = AQUI / "datos"


def sesion() -> requests.Session:
    s = requests.Session()
    s.headers["Authorization"] = "Bearer " + RUTA_TOKEN.read_text(encoding="utf-8").strip()
    return s
