from __future__ import annotations
"""Monta o índice do RAG a partir de duas camadas:

1. AUTOMÁTICA: todo documento em rag/docs é fatiado em trechos de ~120 palavras, sem cruzar
   página (a citação de página fica exata). Metadados vêm de fontes.json ("padrao" e "secoes").
2. CURADA: trechos copiados à mão em rag/curados/*.json, uma conduta por trecho, com tipo,
   subtipo, condição e palavras-chave do ACS. Na busca, pesam mais que os automáticos.

O validador confere se o texto de cada trecho curado aparece de verdade na página citada.
É a garantia de que ninguém inventou conduta.

Uso: python -m rag.indexar
"""
import json
import re
import sys
from pathlib import Path

from app.config import RAG_DIR
from rag.extrair import DOCS, FONTES, carregar_fontes, extrair_tudo, salvar
from rag.texto import para_comparar

CURADOS = RAG_DIR / "curados"
SAIDA = RAG_DIR / "indice" / "trechos.jsonl"

TIPOS = {"primeiros_cuidados", "nao_fazer", "sinais_de_alerta", "quando_voltar", "informacao"}
SUBTIPOS = {"traumatico", "espontaneo", "geral"}
CONDICOES = {"cabeca", "tronco", "membro", "dengue", "cobra", "anticoagulante"}
OBRIGATORIOS = ("id", "texto", "fonte", "pagina", "tipo", "subtipo")

ALVO_PALAVRAS = 120
MAX_PALAVRAS = 200
MIN_PALAVRAS = 15


# ---------- camada automática ----------

def _frases(texto: str) -> list[str]:
    t = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", texto)
    partes = re.split(r"(?<=[.!?;:])\s+|\n\s*\n|\n(?=\s*[•▪●◦\-–]\s)", t)
    return [re.sub(r"\s+", " ", p).strip() for p in partes if p.strip()]


def fatiar(texto: str) -> list[str]:
    """Agrupa frases em blocos de ~ALVO_PALAVRAS, repetindo a última frase (sobreposição)."""
    frases = []
    for f in _frases(texto):
        palavras = f.split()
        # frase gigante (tabela, lista sem pontuação): corta por palavras
        for i in range(0, len(palavras), MAX_PALAVRAS):
            frases.append(" ".join(palavras[i:i + MAX_PALAVRAS]))
    blocos, atual, n = [], [], 0
    for f in frases:
        w = len(f.split())
        if atual and n + w > ALVO_PALAVRAS:
            blocos.append(" ".join(atual))
            ultima = atual[-1]
            atual = [ultima] if len(ultima.split()) < ALVO_PALAVRAS // 2 else []
            n = sum(len(x.split()) for x in atual)
        atual.append(f)
        n += w
    if atual:
        blocos.append(" ".join(atual))
    return [b for b in blocos if len(b.split()) >= MIN_PALAVRAS]


def _intervalo(spec: str) -> set[int]:
    """'10-15, 20' -> {10..15, 20}"""
    paginas = set()
    for parte in str(spec).split(","):
        parte = parte.strip()
        if "-" in parte:
            a, b = parte.split("-")
            paginas.update(range(int(a), int(b) + 1))
        elif parte:
            paginas.add(int(parte))
    return paginas


def metadados_pagina(fonte: dict, pagina: int) -> dict:
    meta = {"subtipo": "geral", "condicao": None, "tipo": "informacao", "palavras_chave": []}
    meta.update(fonte.get("padrao", {}))
    for secao in fonte.get("secoes", []):
        if pagina in _intervalo(secao["paginas"]):
            meta.update({k: v for k, v in secao.items() if k != "paginas"})
    return meta


def trechos_automaticos(fontes: list[dict], paginas: list[dict]) -> list[dict]:
    por_id = {f["id"]: f for f in fontes}
    trechos = []
    for p in paginas:
        fonte = por_id[p["fonte"]]
        meta = metadados_pagina(fonte, p["pagina"])
        for i, bloco in enumerate(fatiar(p["texto"]), start=1):
            trechos.append({
                "id": f"{fonte['id']}_p{p['pagina']}_{i}",
                "origem": "auto",
                "fonte": fonte["id"],
                "fonte_titulo": fonte.get("titulo", fonte["id"]),
                "pagina": p["pagina"],
                "subtipo": meta["subtipo"],
                "condicao": meta["condicao"],
                "tipo": meta["tipo"],
                "texto": bloco,
                "palavras_chave": meta["palavras_chave"],
                "conferido": True,  # veio direto do PDF
            })
    return trechos


# ---------- camada curada ----------

def _texto_na_pagina(texto: str, fonte: str, pagina: int, paginas_idx: dict) -> bool:
    """Confere se o texto (ou cada pedaço entre '...') está na página citada ou nas vizinhas."""
    vizinhas = " ".join(paginas_idx.get((fonte, n), "") for n in (pagina - 1, pagina, pagina + 1))
    alvo = para_comparar(vizinhas)
    pedacos = [para_comparar(p) for p in re.split(r"\[?\.\.\.\]?|…", texto)]
    return all(p in alvo for p in pedacos if len(p) > 10)


def trechos_curados(fontes: list[dict], paginas: list[dict], curados_dir: Path = CURADOS):
    por_id = {f["id"]: f for f in fontes}
    paginas_idx = {(p["fonte"], p["pagina"]): p["texto"] for p in paginas}
    fontes_extraidas = {p["fonte"] for p in paginas}
    trechos, erros, avisos, vistos = [], [], [], set()
    arquivos = sorted(curados_dir.glob("*.json")) if curados_dir.exists() else []
    for arq in arquivos:
        if arq.name.startswith("_"):
            continue  # modelos e exemplos
        try:
            itens = json.loads(arq.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            erros.append(f"{arq.name}: JSON inválido ({e})")
            continue
        for item in itens:
            onde = f"{arq.name} [{item.get('id', '?')}]"
            faltam = [c for c in OBRIGATORIOS if c not in item]
            if faltam:
                erros.append(f"{onde}: faltam campos {faltam}")
                continue
            if item["id"] in vistos:
                erros.append(f"{onde}: id repetido")
                continue
            if item["fonte"] not in por_id:
                erros.append(f"{onde}: fonte '{item['fonte']}' não existe em fontes.json")
                continue
            if item["tipo"] not in TIPOS:
                erros.append(f"{onde}: tipo '{item['tipo']}' inválido; use {sorted(TIPOS)}")
                continue
            if item["subtipo"] not in SUBTIPOS:
                erros.append(f"{onde}: subtipo '{item['subtipo']}' inválido; use {sorted(SUBTIPOS)}")
                continue
            cond = item.get("condicao")
            if cond is not None and cond not in CONDICOES:
                avisos.append(f"{onde}: condição nova '{cond}' (ok, mas o agente só filtra por {sorted(CONDICOES)})")
            conferido = False
            if item["pagina"] is None:
                avisos.append(f"{onde}: sem página; a orientação vai sair sem página")
            elif item["fonte"] not in fontes_extraidas:
                avisos.append(f"{onde}: PDF de '{item['fonte']}' não está em rag/docs; não deu para conferir")
            elif _texto_na_pagina(item["texto"], item["fonte"], item["pagina"], paginas_idx):
                conferido = True
            else:
                avisos.append(f"{onde}: texto NÃO encontrado na página {item['pagina']} de "
                              f"'{item['fonte']}'. Copiou igual ao PDF? Página certa?")
            vistos.add(item["id"])
            trechos.append({
                "id": item["id"],
                "origem": "curado",
                "fonte": item["fonte"],
                "fonte_titulo": por_id[item["fonte"]].get("titulo", item["fonte"]),
                "pagina": item["pagina"],
                "subtipo": item["subtipo"],
                "condicao": cond,
                "tipo": item["tipo"],
                "texto": item["texto"],
                "palavras_chave": item.get("palavras_chave", []),
                "conferido": conferido,  # texto achado na página citada do PDF
            })
    return trechos, erros, avisos


# ---------- pipeline ----------

def indexar(fontes_path: Path = FONTES, docs_dir: Path = DOCS, curados_dir: Path = CURADOS,
            saida: Path = SAIDA) -> int:
    fontes, avisos = carregar_fontes(fontes_path, docs_dir)
    print("Extraindo:")
    paginas, avisos_ext = extrair_tudo(fontes, docs_dir)
    salvar(paginas, saida.parent / "paginas.jsonl")
    auto = trechos_automaticos(fontes, paginas)
    curados, erros, avisos_cur = trechos_curados(fontes, paginas, curados_dir)

    saida.parent.mkdir(parents=True, exist_ok=True)
    with saida.open("w", encoding="utf-8") as f:
        for t in curados + auto:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")

    for a in avisos + avisos_ext + avisos_cur:
        print(f"AVISO {a}")
    for e in erros:
        print(f"ERRO  {e}")
    nao_conf = sum(1 for t in curados if not t["conferido"])
    if nao_conf:
        print(f"\n{nao_conf} trecho(s) curado(s) NÃO conferido(s) no PDF (entram no índice marcados conferido=false).")
    print(f"\n{len(curados)} trechos curados + {len(auto)} automáticos -> {saida.relative_to(saida.parent.parent.parent)}")
    if erros:
        print(f"{len(erros)} trecho(s) curado(s) ficaram FORA do índice por erro.")
    return 1 if erros else 0


if __name__ == "__main__":
    sys.exit(indexar())
