"""Testa se o agente ENTENDE a fala do ACS (campo a campo), antes de qualquer regra.

Mede duas coisas, lado a lado:
  - "modelo": só o LLM (o que o prompt consegue sozinho)
  - "agente": LLM + validação + complemento por palavras + rede de segurança (o que vale no app)

E conta os erros por gravidade:
  - ALERTA PERDIDO: um sinal de alerta que o ACS falou e ficou sem SIM  -> pode virar grave como leve
  - INVENTOU "NÃO": campo de alerta que o ACS NÃO mencionou e virou "não" -> o agente nunca pergunta
  - inventou "não sei"/sim: campo não mencionado que virou sim/"não sei"   -> exagera o risco

Uso:
  python avaliacao/avaliar_extracao.py               # LLM simulado
  python avaliacao/avaliar_extracao.py --llm ollama  # modelo local
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agente import Agente, validar_campos  # noqa: E402
from app.llm import criar_llm  # noqa: E402
from app.modelos import Caso  # noqa: E402
from app.regras import CAMPOS_ALERTA, PERGUNTAS  # noqa: E402

CASOS = Path(__file__).with_name("extracao.json")
ALERTAS = CAMPOS_ALERTA | {"mexe_apoia"}


def _positivo(campo, v):
    """O valor que PREOCUPA: SIM (ou 'não sei'); em mexe_apoia, NÃO."""
    if campo == "mexe_apoia":
        return v is False or v == "nao_sei"
    return v is True or v == "nao_sei"


def _ok(obtido, esperado):
    return obtido in esperado if isinstance(esperado, list) else obtido == esperado


def extrair(agente: Agente, item: dict) -> tuple[dict, dict, float]:
    campo = item.get("campo_perguntado")
    caso = Caso(id=uuid.uuid4().hex[:8], criado_em=datetime.now(), comunidade="teste",
                campo_perguntado=campo, ultima_pergunta=PERGUNTAS.get(campo) if campo else None)
    t0 = time.perf_counter()
    novos = agente._extrair(caso, item["fala"])
    seg = time.perf_counter() - t0
    modelo = {}
    for p in caso.passos:  # o que o LLM disse, validado (antes do complemento por palavras)
        if p.ferramenta == "atualizar_caso" and p.quem == "llm":
            modelo = p.saida
    agente._aplicar(caso, novos)
    agente._rede_seguranca(caso, item["fala"])
    return modelo, caso.campos.model_dump(exclude_none=True), seg


def avaliar(obtido: dict, esperado: dict) -> dict:
    r = {"certos": 0, "total": len(esperado), "erros": {}, "alerta_perdido": [], "inventou_nao": [], "inventou_sim": []}
    for campo, esp in esperado.items():
        v = obtido.get(campo)
        if _ok(v, esp):
            r["certos"] += 1
        else:
            r["erros"][campo] = (v, esp)
            if campo in ALERTAS and any(_positivo(campo, e) for e in (esp if isinstance(esp, list) else [esp])) \
                    and not _positivo(campo, v):
                r["alerta_perdido"].append(campo)
    for campo, v in obtido.items():
        if campo in esperado or campo not in ALERTAS:
            continue
        (r["inventou_sim"] if _positivo(campo, v) else r["inventou_nao"]).append(f"{campo}={v}")
    return r


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", default="mock")
    a = ap.parse_args()
    agente = Agente(criar_llm(a.llm))
    itens = json.loads(CASOS.read_text(encoding="utf-8"))
    soma = {k: {"certos": 0, "total": 0, "alerta_perdido": 0, "inventou_nao": 0, "inventou_sim": 0}
            for k in ("modelo", "agente")}
    tempos = []
    print(f"{len(itens)} falas · LLM: {agente.llm.nome}\n")
    for i, item in enumerate(itens, 1):
        modelo, final, seg = extrair(agente, item)
        tempos.append(seg)
        linhas = []
        for nome, obtido in (("modelo", modelo), ("agente", final)):
            r = avaliar(obtido, item["esperado"])
            s = soma[nome]
            s["certos"] += r["certos"]
            s["total"] += r["total"]
            for k in ("alerta_perdido", "inventou_nao", "inventou_sim"):
                s[k] += len(r[k])
            if r["erros"] or r["alerta_perdido"] or r["inventou_nao"] or r["inventou_sim"]:
                partes = []
                if r["alerta_perdido"]:
                    partes.append(f"ALERTA PERDIDO {r['alerta_perdido']}")
                if r["inventou_nao"]:
                    partes.append(f"INVENTOU NÃO {r['inventou_nao']}")
                if r["inventou_sim"]:
                    partes.append(f"inventou sim {r['inventou_sim']}")
                erros = {k: v for k, v in r["erros"].items() if k not in r["alerta_perdido"]}
                if erros:
                    partes.append(f"erros (obtido, esperado) {erros}")
                linhas.append(f"      {nome}: " + " | ".join(partes))
        marca = "✓" if not linhas else "·"
        pergunta = f"[{item['campo_perguntado']}] " if item.get("campo_perguntado") else ""
        print(f"{i:>2}. {marca} {seg:4.1f}s {pergunta}{item['fala'][:70]!r}")
        for linha in linhas:
            print(linha)

    print("\n=== Placar ===            modelo   agente")
    for rotulo, k in (("Campos certos", None), ("ALERTA PERDIDO (meta 0)", "alerta_perdido"),
                      ("INVENTOU NÃO (meta 0)", "inventou_nao"), ("Inventou sim/não sei", "inventou_sim")):
        if k is None:
            vals = [f"{s['certos']}/{s['total']} ({s['certos'] / s['total']:.0%})" for s in soma.values()]
        else:
            vals = [str(s[k]) for s in soma.values()]
        print(f"{rotulo:<26}{vals[0]:>14}{vals[1]:>14}")
    print(f"Tempo médio por fala: {sum(tempos) / len(tempos):.1f}s (pior {max(tempos):.1f}s)")
    return 1 if soma["agente"]["alerta_perdido"] else 0


if __name__ == "__main__":
    sys.exit(main())
