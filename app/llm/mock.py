"""LLM simulado: responde no mesmo contrato do modelo real, usando palavras-chave.

Serve para o time desenvolver front, regras e RAG sem depender do modelo local.
Com LLM_MOCK_FALHAS=0.3, devolve JSON quebrado 30% das vezes (para testar os guardrails).
"""
import json
import random
import re

from app import palavras
from app.config import LLM_MOCK_FALHAS


class MockLLM:
    nome = "mock (palavras-chave)"

    def __init__(self, taxa_falhas: float = LLM_MOCK_FALHAS, semente: int | None = None):
        self.taxa_falhas = taxa_falhas
        self._rng = random.Random(semente)

    def completar(self, mensagens: list[dict[str, str]]) -> str:
        if self._rng.random() < self.taxa_falhas:
            return "Claro! Aqui está a resposta: {acao: perguntar"  # JSON quebrado de propósito
        pedido = json.loads(mensagens[-1]["content"])
        tarefa = pedido["tarefa"]
        if tarefa == "extrair":
            campos = palavras.extrair(pedido["fala_acs"], pedido.get("campo_perguntado"))
            return json.dumps({"acao": "atualizar_caso", "campos": campos}, ensure_ascii=False)
        if tarefa == "perguntar":
            return json.dumps({"acao": "perguntar", "texto": pedido["pergunta_padrao"]}, ensure_ascii=False)
        if tarefa == "orientar":
            frases = []
            for t in pedido["trechos"]:
                primeira = re.split(r"(?<=[.;])\s", t["texto"])[0].rstrip(".;")
                frases.append(f"{primeira} [{t['id']}].")
            return json.dumps(
                {"fala": " ".join(frases), "citacoes": [t["id"] for t in pedido["trechos"]]},
                ensure_ascii=False,
            )
        raise ValueError(f"tarefa desconhecida: {tarefa}")
