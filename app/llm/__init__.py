from __future__ import annotations
from app.config import LLM_PROVEDOR
from app.llm.base import LLM


def criar_llm(provedor: str = LLM_PROVEDOR) -> LLM:
    if provedor == "mock":
        from app.llm.mock import MockLLM
        return MockLLM()
    if provedor == "ollama":
        from app.llm.ollama import OllamaLLM
        return OllamaLLM()
    raise ValueError(f"LLM_PROVEDOR desconhecido: {provedor}")
