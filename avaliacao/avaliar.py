"""Roda os casos de avaliacao/golden.json pelo agente inteiro e imprime o placar.

Cada caso é a primeira fala do ACS. Se o agente perguntar mais alguma coisa, a resposta é a
"benigna" (o que a fala não mencionou, não tem): não, e "sim" para "consegue mexer?".

Metas do plano técnico:
  - casos graves classificados como leves: ZERO (o script sai com erro se houver)
  - trecho esperado entre os recuperados: 12 de 15 (aqui, proporcional ao número de casos)
  - orientação sem fonte: ZERO

Uso:
  python avaliacao/avaliar.py               # LLM simulado (rápido, determinístico)
  python avaliacao/avaliar.py --llm ollama  # modelo local
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agente import Agente  # noqa: E402
from app.llm import criar_llm  # noqa: E402
from app.regras import ORDEM_COR  # noqa: E402
from app.unidades import comunidades  # noqa: E402

GOLDEN = Path(__file__).with_name("golden.json")
MAX_TURNOS = 12
RESPOSTA_BENIGNA = {
    "pancada": "não sei",
    "local": "não sei",
    "mecanismo": "pancada leve",
    "mexe_apoia": "sim, mexe normal",
    "deformidade": "não, tá normal",
}


def rodar(agente: Agente, caso: dict) -> tuple:
    """caso["respostas"] (opcional) responde perguntas específicas; o resto recebe a resposta benigna."""
    c = agente.novo_caso(caso.get("comunidade", comunidades()[0]), caso.get("idade"))
    c = agente.responder(c, caso["caso"])
    turnos = 1
    respostas = {**RESPOSTA_BENIGNA, **caso.get("respostas", {})}
    while c.status == "coletando" and turnos < MAX_TURNOS:
        c = agente.responder(c, respostas.get(c.campo_perguntado, "não"))
        turnos += 1
    return c, turnos


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", default="mock")
    a = ap.parse_args()
    casos = json.loads(GOLDEN.read_text(encoding="utf-8"))
    agente = Agente(criar_llm(a.llm))

    graves_como_leves = acerto_cor = achou_trecho = sem_fonte = barradas = exagerou = destino_ok = com_destino = 0
    print(f"{len(casos)} casos · LLM: {agente.llm.nome}\n")
    for i, caso in enumerate(casos, 1):
        t0 = time.perf_counter()
        c, turnos = rodar(agente, caso)
        esperada = caso["cor_esperada"]
        obtida = c.classificacao.cor if c.classificacao else "—"
        o = c.orientacao
        ids = [t.id for t in o.trechos] if o else []
        esperados = caso.get("trechos_esperados", [])
        achados = [t for t in esperados if t in ids]

        grave_leve = ORDEM_COR[esperada] >= ORDEM_COR["laranja"] and ORDEM_COR.get(obtida, -1) < ORDEM_COR[esperada]
        graves_como_leves += grave_leve
        acerto_cor += obtida == esperada
        exagerou += ORDEM_COR.get(obtida, -1) > ORDEM_COR[esperada]
        destino = ("casa" if c.destino and c.destino.em_casa else c.destino.unidade_id) if c.destino else None
        dest_esp = caso.get("destino_esperado")
        if dest_esp:
            com_destino += 1
            destino_ok += destino == dest_esp
        achou_trecho += bool(achados) or not esperados
        if o and o.status == "ok" and not o.citacoes:
            sem_fonte += 1
        if o and o.status == "so_trechos":
            barradas += 1

        marca = "✗ GRAVE COMO LEVE" if grave_leve else ("✓" if obtida == esperada else "↑ exagerou" if ORDEM_COR.get(obtida, -1) > ORDEM_COR[esperada] else "≠")
        print(f"{i:>2}. {marca:<18} esperado {esperada:<8} obtido {obtida:<8} "
              f"{turnos} turno(s) {time.perf_counter() - t0:5.1f}s  {caso['caso'][:60]!r}")
        if dest_esp and destino != dest_esp:
            print(f"    destino {destino} (esperado {dest_esp})")
        print(f"    trechos esperados {len(achados)}/{len(esperados)} {esperados}"
              f" | recuperados {ids} | orientação {o.status if o else '—'}")
        if o and o.problemas_verificador:
            print(f"    verificador: {o.problemas_verificador}")

    n = len(casos)
    print("\n=== Placar ===")
    print(f"Casos graves classificados como leves: {graves_como_leves}  (meta: 0)")
    print(f"Cor exata:                             {acerto_cor}/{n}")
    print(f"Cor mais grave que o esperado:         {exagerou}  (seguro, mas manda gente à toa)")
    print(f"Destino certo:                         {destino_ok}/{com_destino}")
    print(f"Algum trecho esperado recuperado:      {achou_trecho}/{n}  (meta: {round(n * 12 / 15)}/{n})")
    print(f"Orientações sem fonte:                 {sem_fonte}  (meta: 0)")
    print(f"Orientações barradas pelo verificador: {barradas}")
    return 1 if graves_como_leves or sem_fonte else 0


if __name__ == "__main__":
    sys.exit(main())
