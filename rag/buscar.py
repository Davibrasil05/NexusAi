"""Busca BM25 sobre o índice, com filtro por metadados e nota mínima.

Uso (para testar o que foi adicionado):
  python -m rag.buscar "mancha roxa febre gengiva sangrando"
  python -m rag.buscar "pancada cabeça vômito" --subtipo traumatico --condicao cabeca
  python -m rag.buscar "picada cobra" --so-curados -k 3
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from rank_bm25 import BM25Okapi

from app.config import RAG_LIMIAR, RAG_TOP_K
from rag.indexar import SAIDA as INDICE
from rag.texto import tokenizar

PESO_CURADO = 1.5  # trecho curado à mão vale mais que um pedaço automático do PDF


class Buscador:
    def __init__(self, indice: Path = INDICE):
        if not indice.exists():
            raise FileNotFoundError(f"{indice} não existe. Rode: python -m rag.indexar")
        with indice.open(encoding="utf-8") as f:
            self.trechos = [json.loads(linha) for linha in f]
        if not self.trechos:
            raise ValueError("índice vazio: adicione documentos em rag/docs ou trechos em rag/curados")
        corpus = [tokenizar(t["texto"] + " " + " ".join(t["palavras_chave"])) for t in self.trechos]
        self.bm25 = BM25Okapi(corpus)

    def buscar(self, consulta: str, subtipo: str | None = None, condicoes: set[str] | None = None,
               tipos: set[str] | None = None, k: int = RAG_TOP_K, limiar: float = RAG_LIMIAR,
               so_curados: bool = False, cor: str | None = None) -> list[dict]:
        """Filtro vem do CASO (subtipo, condições), não da pergunta livre.

        subtipo=None não filtra; com subtipo, entram os do subtipo e os 'geral'.
        condicoes=None não filtra; com um conjunto, entram trechos sem condição ou com condição do caso.
        """
        notas = self.bm25.get_scores(tokenizar(consulta))
        achados = []
        for t, nota in zip(self.trechos, notas):
            if subtipo and t["subtipo"] not in (subtipo, "geral"):
                continue
            if condicoes is not None and t["condicao"] is not None and t["condicao"] not in condicoes:
                continue
            if tipos and t["tipo"] not in tipos:
                continue
            if so_curados and t["origem"] != "curado":
                continue
            if cor and t.get("cores") and cor not in t["cores"]:
                continue  # ex.: "hematoma antigo, pode ficar em casa" só vale para verde/amarelo
            nota = float(nota) * (PESO_CURADO if t["origem"] == "curado" else 1.0)
            if nota >= limiar:
                achados.append({**t, "nota": round(nota, 2)})
        achados.sort(key=lambda t: t["nota"], reverse=True)
        return achados[:k]


def main() -> None:
    ap = argparse.ArgumentParser(description="Testa a busca do RAG")
    ap.add_argument("consulta")
    ap.add_argument("--subtipo", choices=["traumatico", "espontaneo"])
    ap.add_argument("--condicao", action="append", help="pode repetir: --condicao dengue --condicao anticoagulante")
    ap.add_argument("--tipo", action="append")
    ap.add_argument("-k", type=int, default=5)
    ap.add_argument("--limiar", type=float, default=RAG_LIMIAR)
    ap.add_argument("--so-curados", action="store_true")
    a = ap.parse_args()

    try:
        b = Buscador()
    except (FileNotFoundError, ValueError) as e:
        raise SystemExit(str(e))
    res = b.buscar(a.consulta, a.subtipo, set(a.condicao) if a.condicao else None,
                   set(a.tipo) if a.tipo else None, a.k, a.limiar, a.so_curados)
    print(f"{len(b.trechos)} trechos no índice; {len(res)} passaram da nota mínima {a.limiar}\n")
    if not res:
        print("Sem trecho: o app diria 'sem protocolo para essa situação, contate a unidade'.")
    for i, t in enumerate(res, 1):
        pag = f"p.{t['pagina']}" if t["pagina"] else "sem página"
        meta = "/".join(x for x in (t["subtipo"], t["condicao"], t["tipo"]) if x)
        alerta = "  ⚠ NÃO CONFERIDO NO PDF" if not t.get("conferido", True) else ""
        print(f"{i}. [{t['nota']:.2f}] {t['id']}  ({t['origem']}, {t['fonte']} {pag}, {meta}){alerta}")
        texto = t["texto"]
        print(f"   {texto[:300]}{'…' if len(texto) > 300 else ''}\n")


if __name__ == "__main__":
    main()
