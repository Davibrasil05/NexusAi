"""Teste do modelo local com falas de ACS em português informal.

Critérios do plano técnico (o modelo precisa passar nos três):
  1. responde em JSON válido
  2. entende português informal (acerta os campos da fala)
  3. leva até ~10 segundos por resposta

Uso:
  python scripts/testar_modelo.py                      # usa LLM_MODELO
  python scripts/testar_modelo.py qwen3:8b gemma3:12b  # compara vários
"""
from __future__ import annotations
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import LLM_MODELO, OLLAMA_BASE_URL  # noqa: E402
from app.llm.ollama import OllamaLLM  # noqa: E402
from app.prompts import extrair  # noqa: E402  (mesmo prompt que o agente usa)

LIMITE_SEGUNDOS = 10
META_ACERTO = 0.8

# (fala do ACS, campos esperados)
FALAS = [
    ("ela caiu do açaizeiro e bateu a cabeça, depois vomitou duas vez",
     {"pancada": True, "local": "cabeca", "mecanismo": "queda_altura", "sinais_cabeca": True}),
    ("tá com umas mancha roxa na perna, não teve pancada não, tá com febre faz 4 dia e a gengiva sangrando",
     {"pancada": False, "local": "perna", "febre": True, "sangramento_mucosa": True}),
    ("bateu a canela no banco, tá roxinho mas anda normal",
     {"pancada": True, "local": "perna", "mecanismo": "pancada_leve", "mexe_apoia": True}),
    ("o menino levou uma pancada de remo no braço, tá torto e ele não mexe",
     {"pancada": True, "local": "braco", "deformidade": True, "mexe_apoia": False}),
    ("a vó toma melhoral todo dia, apareceu uma mancha roxa no braço sozinha",
     {"pancada": False, "local": "braco", "anticoagulante": True}),
]


def mensagens(fala: str) -> list[dict]:
    return extrair(fala, campo_perguntado="pancada", pergunta="Conte o que aconteceu. Teve pancada ou queda?",
                   campos_conhecidos={})


def testar(modelo: str) -> dict:
    llm = OllamaLLM(modelo=modelo, timeout_s=60)
    print(f"\n=== {modelo} ===")
    t0 = time.perf_counter()
    llm.completar(mensagens("teste"))  # aquecimento: carrega o modelo na memória, fora da medição
    print(f"carregou em {time.perf_counter() - t0:.1f}s")

    json_ok = acertos = total = 0
    tempos = []
    for fala, esperado in FALAS:
        t0 = time.perf_counter()
        try:
            bruto = llm.completar(mensagens(fala))
        except Exception as e:  # timeout, conexão
            bruto = f"ERRO: {e}"
        seg = time.perf_counter() - t0
        tempos.append(seg)
        try:
            campos = json.loads(bruto)["campos"]
            assert isinstance(campos, dict)
            json_ok += 1
        except Exception:
            campos = {}
        certos = [k for k, v in esperado.items() if campos.get(k) == v]
        acertos += len(certos)
        total += len(esperado)
        errados = {k: (campos.get(k), v) for k, v in esperado.items() if k not in certos}
        print(f"{seg:5.1f}s  {len(certos)}/{len(esperado)}  {fala[:55]!r}")
        if errados:
            print(f"        erros (obtido, esperado): {errados}")
        if not campos:
            print(f"        resposta crua: {bruto[:200]!r}")

    taxa = acertos / total
    pior = max(tempos)
    r = {
        "modelo": modelo,
        "json_valido": f"{json_ok}/{len(FALAS)}",
        "acerto": f"{taxa:.0%}",
        "tempo_medio_s": round(sum(tempos) / len(tempos), 1),
        "pior_tempo_s": round(pior, 1),
        "passa": json_ok == len(FALAS) and taxa >= META_ACERTO and pior <= LIMITE_SEGUNDOS,
    }
    return r


def main() -> None:
    modelos = sys.argv[1:] or [LLM_MODELO]
    try:
        instalados = OllamaLLM().modelos_instalados()
    except Exception as e:
        sys.exit(f"Ollama não respondeu em {OLLAMA_BASE_URL} ({e}).\nAbra o app do Ollama ou rode: ollama serve")
    faltando = [m for m in modelos if m not in instalados]
    if faltando:
        sys.exit(f"Modelos não baixados: {faltando}\nInstalados: {instalados}\nBaixe com: ollama pull <modelo>")

    resultados = [testar(m) for m in modelos]
    print("\n=== Placar ===")
    print(f"{'modelo':<24}{'JSON':>6}{'acerto':>8}{'média':>8}{'pior':>7}  passa")
    for r in resultados:
        print(f"{r['modelo']:<24}{r['json_valido']:>6}{r['acerto']:>8}{r['tempo_medio_s']:>7}s"
              f"{r['pior_tempo_s']:>6}s  {'SIM' if r['passa'] else 'não'}")


if __name__ == "__main__":
    main()
