from __future__ import annotations
"""Normalização de texto compartilhada entre indexação e busca (tudo offline)."""
import re

from unidecode import unidecode

STOPWORDS = set("""
a o e de do da dos das em no na nos nas um uma uns umas para pra por com sem que se ou ao aos as os
ser sao foi era como mais menos muito muita ja nao sim ter tem ha isso esse essa este esta estes estas
pelo pela pelos pelas seu sua seus suas ele ela eles elas lhe quando onde qual quais ate sobre entre
apos antes deve devem pode podem caso casos outro outra outros outras ainda tambem mesmo todo toda
todos todas cada sua nas numa num ou seja sendo sido esta estao
""".split())

TAMANHO_RADICAL = 6  # "sangramento", "sangrando", "sangrar" -> "sangra"


def normalizar(texto: str) -> str:
    """Minúsculas, sem acento, sem hifenização de quebra de linha, espaços simples."""
    t = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", texto)
    t = unidecode(t).lower()
    return re.sub(r"\s+", " ", t).strip()


def tokenizar(texto: str) -> list[str]:
    """Tokens para o BM25: sem stopwords, sem números, radical por truncamento."""
    tokens = re.findall(r"[a-z]+", normalizar(texto))
    return [t[:TAMANHO_RADICAL] for t in tokens if len(t) > 1 and t not in STOPWORDS]


def para_comparar(texto: str) -> str:
    """Forma usada para conferir se um trecho curado existe mesmo na página do PDF."""
    return re.sub(r"[^a-z0-9]+", " ", normalizar(texto)).strip()
