"""Configuração lida de variáveis de ambiente. Nada aqui acessa a internet."""
from __future__ import annotations
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "dados"
FOTOS = DADOS / "fotos"
RAG_DIR = RAIZ / "rag"
WEB = RAIZ / "web"

# "mock" funciona sem modelo nenhum (para o time trabalhar em paralelo).
# "ollama" usa o modelo local (app/llm/ollama.py).
LLM_PROVEDOR = os.getenv("LLM_PROVEDOR", "mock")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
LLM_MODELO = os.getenv("LLM_MODELO", "qwen3:8b")
LLM_TIMEOUT_S = float(os.getenv("LLM_TIMEOUT_S", "30"))
# Probabilidade (0 a 1) de o mock devolver JSON quebrado, para testar os guardrails.
LLM_MOCK_FALHAS = float(os.getenv("LLM_MOCK_FALHAS", "0"))

# False = o agente usa a pergunta padrão do código, sem chamar o LLM (metade das chamadas).
# Plano B se o modelo estiver lento.
LLM_REESCREVE_PERGUNTA = os.getenv("LLM_REESCREVE_PERGUNTA", "1") == "1"

RAG_LIMIAR = float(os.getenv("RAG_LIMIAR", "0.5"))
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "4"))

# Quantas vezes o agente pergunta o mesmo campo antes de assumir o pior cenário.
MAX_TENTATIVAS = 2
