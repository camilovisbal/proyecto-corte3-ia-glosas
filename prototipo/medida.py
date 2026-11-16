"""Conteo de tokens con el tokenizador oficial de Qwen3 (el del modelo elegido)."""
from tokenizers import Tokenizer

from comun import AQUI

_TOK = Tokenizer.from_file(str(AQUI.parent / "tokenizador" / "Qwen3-32B-tokenizer.json"))


def contar_tokens(texto: str) -> int:
    return len(_TOK.encode(texto or "", add_special_tokens=False).ids)
