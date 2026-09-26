from __future__ import annotations
"""Cliente do modelo local via Ollama (API no formato OpenAI).

Trocar de modelo ou de servidor muda só LLM_MODELO / OLLAMA_BASE_URL.
Tudo roda em localhost: com o wi-fi desligado continua funcionando.
"""
import re

from openai import BadRequestError, OpenAI

from app.config import LLM_MODELO, LLM_TIMEOUT_S, OLLAMA_BASE_URL

# Modelos com "raciocínio" (ex.: Qwen3, DeepSeek-R1) podem devolver <think>...</think> antes do JSON.
RE_THINK = re.compile(r"<think>.*?</think>", re.DOTALL)


class OllamaLLM:
    def __init__(self, base_url: str = OLLAMA_BASE_URL, modelo: str = LLM_MODELO, timeout_s: float = LLM_TIMEOUT_S):
        self.base_url = base_url
        self.modelo = modelo
        self.nome = f"ollama:{modelo}"
        # api_key é obrigatória no SDK, mas o Ollama ignora.
        # max_retries=0: quem decide tentar de novo é o agente (1 nova tentativa, depois fallback).
        self._cliente = OpenAI(base_url=base_url, api_key="ollama", timeout=timeout_s, max_retries=0)
        # Desliga o "raciocínio" (Qwen3 pensa ~8 mil caracteres antes de responder: 25 s -> 3 s).
        # Se o modelo não aceitar o parâmetro, tentamos de novo sem ele e não mandamos mais.
        self._sem_raciocinio = True

    def completar(self, mensagens: list[dict[str, str]]) -> str:
        kwargs = {
            "model": self.modelo,
            "messages": mensagens,
            "temperature": 0,
            "response_format": {"type": "json_object"},  # o Ollama força a saída a ser JSON
        }
        if self._sem_raciocinio:
            kwargs["reasoning_effort"] = "none"
        try:
            resp = self._cliente.chat.completions.create(**kwargs)
        except BadRequestError as e:
            if "reasoning_effort" not in kwargs or "think" not in str(e).lower():
                raise
            self._sem_raciocinio = False
            del kwargs["reasoning_effort"]
            resp = self._cliente.chat.completions.create(**kwargs)
        texto = resp.choices[0].message.content or ""
        return RE_THINK.sub("", texto).strip()

    def modelos_instalados(self) -> list[str]:
        return sorted(m.id for m in self._cliente.models.list().data)
