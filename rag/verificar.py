"""Verificador da orientação escrita pelo LLM.

Barra a fala se: não cita nada, cita id que não foi recuperado, ou menciona remédio/dose
que não está nos trechos citados. Se barrar, o app mostra só os trechos originais.
"""
from __future__ import annotations
import re

from rag.texto import normalizar

REMEDIOS = [
    "aas", "acido acetilsalicilico", "aspirina", "melhoral", "ibuprofeno", "diclofenaco", "nimesulida",
    "cetoprofeno", "naproxeno", "dipirona", "paracetamol", "dorflex", "antibiotico", "amoxicilina",
    "cefalexina", "corticoide", "dexametasona", "prednisona", "varfarina", "heparina", "vitamina k",
    "pomada", "hirudoid", "soro antiofidico", "tramadol", "morfina", "codeina", "buscopan", "anti inflamatorio",
]
RE_DOSE = re.compile(r"\b\d+(?:[.,]\d+)?\s*(?:mg|mcg|g|ml|gotas?|comprimidos?|cp|ui|colher(?:es)?)\b")
RE_CITACAO = re.compile(r"\[([\w\-]+)\]")


def _norm(t: str) -> str:
    return re.sub(r"[^a-z0-9.,]+", " ", normalizar(t))


MIN_PALAVRAS_FRASE = 4  # abaixo disso é resto de pontuação ("." depois da citação), não frase


def _frases(texto: str) -> list[str]:
    return [f for f in re.split(r"(?<=[.!?])\s+|(?<=[.!?])$", texto)
            if len(re.findall(r"\w+", f)) >= MIN_PALAVRAS_FRASE]


def frases_sem_fonte(fala: str) -> list[str]:
    """Cada frase precisa de uma citação logo depois. Devolve as frases que ficaram sem.

    "A [x]. B. [y]" -> ok;  "A [x]. B. C. [y]" -> "B." sem fonte;  "A [x]. B." -> "B." sem fonte.
    """
    partes = RE_CITACAO.split(fala)  # texto, id, texto, id, ..., texto
    sem = []
    for i in range(0, len(partes), 2):
        frases = _frases(partes[i])
        citado = i + 1 < len(partes)
        sem += frases[:-1] if citado else frases  # só a última frase antes da citação é coberta
    return [f.strip() for f in sem]


def verificar(fala: str, citacoes: list[str], trechos: list[dict]) -> list[str]:
    """Lista de problemas (vazia = aprovado)."""
    ids = {t["id"] for t in trechos}
    problemas = []
    todas = set(citacoes) | set(RE_CITACAO.findall(fala))
    if not todas:
        problemas.append("nenhuma citação")
    invalidas = sorted(todas - ids)
    if invalidas:
        problemas.append(f"cita trecho que não foi recuperado: {invalidas}")
    for f in frases_sem_fonte(fala):
        problemas.append(f"frase sem fonte: {f[:80]}")
    base = _norm(" ".join(t["texto"] for t in trechos if t["id"] in todas))
    texto = _norm(RE_CITACAO.sub(" ", fala))
    for r in REMEDIOS:
        if re.search(rf"\b{r}\b", texto) and not re.search(rf"\b{r}\b", base):
            problemas.append(f"remédio fora dos trechos: {r}")
    for dose in RE_DOSE.findall(texto):
        if dose not in base:
            problemas.append(f"dose fora dos trechos: {dose}")
    return problemas
