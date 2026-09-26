"""Extrai o texto dos documentos de rag/docs, página por página.

Aceita .pdf, .txt e .md. Em .txt/.md, o caractere de quebra de página (\\f) separa as páginas.
Qualquer arquivo em rag/docs sem cadastro em rag/fontes.json é cadastrado automaticamente
com metadados genéricos (e um aviso), para nada ficar de fora.

Uso: python -m rag.extrair
"""
import json
import re
import sys
from pathlib import Path

import pymupdf

from app.config import RAG_DIR

DOCS = RAG_DIR / "docs"
FONTES = RAG_DIR / "fontes.json"
SAIDA = RAG_DIR / "indice" / "paginas.jsonl"
EXTENSOES = {".pdf", ".txt", ".md"}
MIN_PALAVRAS_PAGINA = 30  # abaixo disso a página é capa, sumário ou imagem


def carregar_fontes(fontes_path: Path = FONTES, docs_dir: Path = DOCS) -> tuple[list[dict], list[str]]:
    """Fontes cadastradas + arquivos soltos em docs/ cadastrados automaticamente."""
    fontes = json.loads(fontes_path.read_text(encoding="utf-8")) if fontes_path.exists() else []
    avisos = []
    cadastrados = {f["arquivo"] for f in fontes}
    for arq in sorted(docs_dir.iterdir()):
        if arq.suffix.lower() in EXTENSOES and arq.name not in cadastrados:
            fid = re.sub(r"[^a-z0-9]+", "_", arq.stem.lower()).strip("_")
            fontes.append({"id": fid, "titulo": arq.stem, "arquivo": arq.name, "padrao": {"subtipo": "geral"}})
            avisos.append(f"{arq.name}: sem cadastro em fontes.json; usei id '{fid}' e subtipo 'geral'")
    return fontes, avisos


def extrair_arquivo(caminho: Path) -> list[tuple[int, str]]:
    """[(pagina, texto)] com página começando em 1 (a mesma que o leitor de PDF mostra)."""
    if caminho.suffix.lower() == ".pdf":
        with pymupdf.open(caminho) as doc:
            return [(i + 1, pagina.get_text("text")) for i, pagina in enumerate(doc)]
    texto = caminho.read_text(encoding="utf-8", errors="replace")
    return [(i + 1, p) for i, p in enumerate(texto.split("\f"))]


def extrair_tudo(fontes: list[dict], docs_dir: Path = DOCS) -> tuple[list[dict], list[str]]:
    paginas, avisos = [], []
    for fonte in fontes:
        caminho = docs_dir / fonte["arquivo"]
        if not caminho.exists():
            avisos.append(f"{fonte['id']}: arquivo '{fonte['arquivo']}' não está em rag/docs; pulei")
            continue
        extraidas = extrair_arquivo(caminho)
        ignorar = set(fonte.get("ignorar_paginas", []))
        uteis = 0
        for n, texto in extraidas:
            if n in ignorar:
                continue
            paginas.append({"fonte": fonte["id"], "pagina": n, "texto": texto})
            if len(texto.split()) >= MIN_PALAVRAS_PAGINA:
                uteis += 1
        print(f"  {fonte['id']:<24} {len(extraidas):>4} páginas, {uteis:>4} com texto")
        if extraidas and uteis == 0:
            avisos.append(f"{fonte['id']}: nenhuma página com texto. PDF escaneado? Precisa de OCR")
    return paginas, avisos


def salvar(paginas: list[dict], saida: Path = SAIDA) -> None:
    saida.parent.mkdir(parents=True, exist_ok=True)
    with saida.open("w", encoding="utf-8") as f:
        for p in paginas:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")


def main() -> None:
    fontes, avisos = carregar_fontes()
    print("Extraindo:")
    paginas, avisos2 = extrair_tudo(fontes)
    salvar(paginas)
    for a in avisos + avisos2:
        print(f"AVISO {a}")
    print(f"{len(paginas)} páginas -> {SAIDA.relative_to(RAG_DIR.parent)}")


if __name__ == "__main__":
    sys.exit(main())
