"""Contrato entre o agente e qualquer modelo (mock, Ollama, MLX...).

O agente só conhece esta interface. Trocar de modelo = trocar a implementação.

Formato das mensagens (padrão OpenAI):
    [{"role": "system", "content": "..."}, {"role": "user", "content": "<JSON>"}]

A mensagem do usuário é SEMPRE um JSON com a chave "tarefa":
    "extrair"   -> o modelo devolve {"acao": "atualizar_caso", "campos": {...}}
    "perguntar" -> o modelo devolve {"acao": "perguntar", "texto": "..."}
    "orientar"  -> o modelo devolve {"fala": "...", "citacoes": ["id", ...]}

O modelo devolve TEXTO. Quem faz o parse e a validação (Pydantic) é o agente.
Se o modelo cair, demorar ou errar, o agente usa o fallback do código.
"""
from __future__ import annotations
from typing import Protocol


class LLM(Protocol):
    nome: str

    def completar(self, mensagens: list[dict[str, str]]) -> str:
        """Recebe as mensagens e devolve o texto cru da resposta (esperado: um JSON).

        Pode levantar exceção (timeout, conexão). O agente trata como falha e usa o fallback.
        """
        ...
