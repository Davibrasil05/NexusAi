"""buscar_unidades: escolhe o destino pelo RECURSO necessário, não pela distância.

Entre as unidades que têm todos os recursos do caso, fica a de menor tempo de barco.
Se a mais próxima não serve, a explicação diz o que falta nela (é o que a demo mostra).
"""
from __future__ import annotations
import json
from functools import lru_cache

from app.config import DADOS
from app.modelos import Destino

REVISITA = "Fica em casa, com revisita do ACS em 24 a 48 horas."


@lru_cache
def carregar() -> dict:
    return json.loads((DADOS / "unidades.json").read_text(encoding="utf-8"))


def comunidades() -> list[str]:
    return carregar()["comunidades"]


def resolver_comunidade(texto: str) -> str:
    """O ACS digita a comunidade. Se bater com uma cadastrada (sem acento/maiúscula), usa o nome oficial."""
    from unidecode import unidecode
    chave = lambda t: " ".join(unidecode(t).lower().split())
    digitado = chave(texto)
    for c in comunidades():
        if chave(c) == digitado:
            return c
    return " ".join(texto.split())


def _nomes(recursos) -> str:
    nomes = carregar()["recursos_nomes"]
    lista = [nomes.get(r, r) for r in recursos]
    return lista[0] if len(lista) == 1 else ", ".join(lista[:-1]) + " e " + lista[-1]


def _minutos(m: int) -> str:
    h, mi = divmod(m, 60)
    if not h:
        return f"{mi} min"
    return f"{h}h{mi:02d}" if mi else f"{h}h"


def buscar_unidades(recursos: list[str], comunidade: str) -> Destino:
    if not recursos:
        return Destino(em_casa=True, explicacao=REVISITA)
    if comunidade not in comunidades():
        raise ValueError(f"comunidade '{comunidade}' não cadastrada em dados/unidades.json")

    precisa = set(recursos)
    unidades = sorted(carregar()["unidades"], key=lambda u: u["tempo_barco_min"][comunidade])
    mais_proxima = unidades[0]
    completas = [u for u in unidades if precisa <= set(u["recursos"])]
    if completas:
        escolhida, faltando = completas[0], []
    else:
        # nenhuma tem tudo: a que cobre mais recursos (empate: a mais perto)
        escolhida = max(unidades, key=lambda u: (len(precisa & set(u["recursos"])), -u["tempo_barco_min"][comunidade]))
        faltando = [r for r in recursos if r not in escolhida["recursos"]]

    tempo = escolhida["tempo_barco_min"][comunidade]
    explicacao = f"Precisa de {_nomes(recursos)}: {escolhida['nome']}, {_minutos(tempo)} de barco."
    if escolhida is not mais_proxima:
        sem = [r for r in recursos if r not in mais_proxima["recursos"]]
        explicacao += (f" A mais próxima ({mais_proxima['nome']}, "
                       f"{_minutos(mais_proxima['tempo_barco_min'][comunidade])}) não tem {_nomes(sem)}.")
    if faltando:
        explicacao += f" Atenção: nenhuma unidade tem {_nomes(faltando)}; avisar a regulação."

    return Destino(
        unidade_id=escolhida["id"],
        nome=escolhida["nome"],
        tempo_barco_min=tempo,
        recursos_atendidos=[r for r in recursos if r in escolhida["recursos"]],
        recursos_faltando=faltando,
        explicacao=explicacao,
    )
