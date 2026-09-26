"""Conversa com o agente no terminal (checkpoint "agente no terminal, offline").

Uso:
  python scripts/conversar.py                         # LLM simulado (mock)
  python scripts/conversar.py --llm ollama --passos   # modelo local + painel de raciocínio
  python scripts/conversar.py --roteiro "manchas roxas na perna, sem pancada|sim|não"
      (falas separadas por '|': roda sozinho, bom para testar)
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
from app.unidades import comunidades  # noqa: E402

CORES_QUEM = {"llm": "35", "codigo": "36", "rag": "32", "guardrail": "33", "pessoa": "37"}
CORES_RISCO = {"vermelho": "41;97", "laranja": "43;30", "amarelo": "103;30", "verde": "42;97"}


def c(texto: str, cod: str) -> str:
    return f"\033[{cod}m{texto}\033[0m" if sys.stdout.isatty() else texto


def mostrar_passos(passos) -> None:
    for p in passos:
        saida = json.dumps(p.saida, ensure_ascii=False, default=str)
        if len(saida) > 160:
            saida = saida[:160] + "…"
        tempo = f" {p.ms}ms" if p.ms else ""
        print(c(f"   · {p.ferramenta} [{p.quem}]{tempo} → {saida}", CORES_QUEM.get(p.quem, "0")))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", default=None, help="mock | ollama (padrão: LLM_PROVEDOR)")
    ap.add_argument("--idade", type=int)
    ap.add_argument("--comunidade", default=comunidades()[0], choices=comunidades())
    ap.add_argument("--passos", action="store_true", help="mostra o painel de raciocínio")
    ap.add_argument("--sem-reescrever", action="store_true", help="usa a pergunta padrão, sem LLM (mais rápido)")
    ap.add_argument("--roteiro", help="falas do ACS separadas por '|'")
    a = ap.parse_args()

    llm = criar_llm(a.llm) if a.llm else criar_llm()
    agente = Agente(llm, reescreve_pergunta=not a.sem_reescrever)
    roteiro = [f.strip() for f in a.roteiro.split("|")] if a.roteiro else None
    print(c(f"Modelo: {llm.nome}", "2"))

    caso = agente.novo_caso(a.comunidade, a.idade)
    visto = 0
    inicio = time.perf_counter()
    while caso.status == "coletando":
        if a.passos:
            mostrar_passos(caso.passos[visto:])
        visto = len(caso.passos)
        print(c(f"\nAgente: {caso.ultima_pergunta}", "1"))
        if roteiro is not None:
            if not roteiro:
                print("(roteiro acabou antes do fim da coleta)")
                break
            texto = roteiro.pop(0)
            print(f"ACS: {texto}")
        else:
            try:
                texto = input("ACS: ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return
            if not texto:
                continue
        caso = agente.responder(caso, texto)

    if a.passos:
        mostrar_passos(caso.passos[visto:])
    if caso.classificacao:
        cls = caso.classificacao
        print("\n" + c(f" {cls.cor.upper()} ", CORES_RISCO[cls.cor]) + " " + "; ".join(cls.motivos))
        if cls.recursos:
            print(f"Recursos necessários no destino: {', '.join(cls.recursos)}")
        if caso.assumidos:
            print(f"Pior cenário assumido em: {', '.join(caso.assumidos)}")
    if caso.destino:
        print(c(f"Destino: {caso.destino.explicacao}", "1"))
    o = caso.orientacao
    if o:
        if o.status == "sem_protocolo":
            print(c("Orientação: sem protocolo para essa situação, contate a unidade.", "33"))
        else:
            if o.status == "ok":
                print(c(f"\nOrientação: {o.fala}", "1"))
            else:
                print(c(f"\nOrientação barrada ({'; '.join(o.problemas_verificador)}). Trechos originais:", "33"))
            for t in o.trechos:
                pag = f"p.{t.pagina}" if t.pagina else "sem página"
                aviso = " ⚠ não conferido no PDF" if not t.conferido else ""
                print(f"  [{t.id}] {t.texto[:220]}{'…' if len(t.texto) > 220 else ''}")
                print(c(f"      — {t.fonte_titulo}, {pag}{aviso}", "2"))

    chamadas = [p for p in caso.passos if p.ferramenta in ("atualizar_caso", "perguntar")]
    falhas = [p for p in caso.passos if p.quem == "guardrail"]
    print(c(f"\nCampos: {caso.campos.model_dump(exclude_none=True)}", "2"))
    print(c(f"{len(chamadas)} chamadas ao LLM, {len(falhas)} passos de guardrail, "
            f"{time.perf_counter() - inicio:.1f}s no total", "2"))


if __name__ == "__main__":
    main()
