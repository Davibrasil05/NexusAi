"""Loop de coleta do agente.

Quem decide o quê:
- As REGRAS (app/regras.py) dizem O QUE perguntar (próximo campo que falta) e dão a cor.
- O LLM decide COMO perguntar e interpreta a fala do ACS em campos do caso.
- Os GUARDRAILS garantem que o LLM nunca baixa o risco:
    * JSON inválido -> 1 nova tentativa -> fallback do código (pergunta padrão / palavras-chave)
    * campo de alerta que já é SIM não volta para NÃO
    * rede de segurança: alerta citado no texto bruto é marcado mesmo se o LLM não marcou
    * sinal de alerta é checado a CADA turno: vermelho na hora, sem terminar a coleta
    * campo perguntado MAX_TENTATIVAS vezes sem resposta -> assume o pior cenário

Cada passo fica em caso.passos (é o que o painel de raciocínio mostra).
"""
import json
import re
import time
import uuid
from datetime import datetime
from typing import Any, Callable

from pydantic import BaseModel, ValidationError

from app import palavras, prompts
from app.config import LLM_REESCREVE_PERGUNTA, MAX_TENTATIVAS
from app.llm.base import LLM
from app import orientador
from app.modelos import (AcaoAtualizar, AcaoPerguntar, CamposCaso, Caso, Mensagem, Orientacao, RespostaOrientar,
                         TrechoRecuperado)
from app.regras import CAMPOS_ALERTA, PERGUNTAS, PIOR_CENARIO, classificar
from app.unidades import buscar_unidades
from rag.verificar import RE_CITACAO, verificar

NOMES_COR = {"vermelho": "VERMELHO", "laranja": "LARANJA", "amarelo": "AMARELO", "verde": "VERDE"}
_SIM = {"sim", "s", "true", "yes"}
_NAO = {"nao", "não", "n", "false", "no"}
_NAO_SEI = {"nao_sei", "nao sei", "não sei", "desconhecido", "unknown"}


class CasoEncerrado(Exception):
    pass


def extrair_json(bruto: str) -> Any:
    """Tira cercas ``` e texto em volta; devolve o primeiro objeto JSON."""
    t = re.sub(r"```(?:json)?", "", bruto)
    ini, fim = t.find("{"), t.rfind("}")
    if ini == -1 or fim <= ini:
        raise ValueError("resposta sem objeto JSON")
    return json.loads(t[ini:fim + 1])


def _normalizar_valor(v: Any) -> Any:
    """Aceita 'sim'/'não'/'não sei' em português vindos do modelo."""
    if isinstance(v, str):
        s = v.strip().lower()
        if s in _SIM:
            return True
        if s in _NAO:
            return False
        if s in _NAO_SEI:
            return "nao_sei"
        return s
    return v


def validar_campos(campos: dict) -> tuple[dict, dict]:
    """Valida campo a campo. Devolve (válidos, rejeitados com o motivo)."""
    validos, rejeitados = {}, {}
    for nome, valor in campos.items():
        if nome not in CamposCaso.model_fields:
            rejeitados[nome] = "campo desconhecido"
            continue
        valor = _normalizar_valor(valor)
        if valor is None:
            continue
        try:
            validos[nome] = getattr(CamposCaso.model_validate({nome: valor}), nome)
        except ValidationError:
            rejeitados[nome] = f"valor inválido: {valor!r}"
    return validos, rejeitados


def _piora(campo: str, atual: Any, novo: Any) -> bool:
    """True se trocar 'atual' por 'novo' aumenta o risco (única troca permitida)."""
    positivo = novo is True or novo == "nao_sei"
    if campo in CAMPOS_ALERTA:
        return (atual is False and positivo) or (atual == "nao_sei" and novo is True)
    if campo == "mexe_apoia":
        return (atual is True and (novo is False or novo == "nao_sei")) or (atual == "nao_sei" and novo is False)
    return False


class Agente:
    def __init__(self, llm: LLM, reescreve_pergunta: bool = LLM_REESCREVE_PERGUNTA, buscador=None):
        self.llm = llm
        self.reescreve_pergunta = reescreve_pergunta
        self._buscador = buscador  # rag.buscar.Buscador; carregado na 1ª orientação se não vier pronto

    # ---------- API pública ----------

    def novo_caso(self, comunidade: str, idade: int | None = None) -> Caso:
        caso = Caso(id=uuid.uuid4().hex[:8], criado_em=datetime.now(), comunidade=comunidade, idade=idade)
        caso.registrar("abrir_caso", "pessoa", entrada={"idade": idade, "comunidade": comunidade})
        # A primeira pergunta é fixa (divide trauma x doença) e não passa pelo LLM.
        self._perguntar(caso, "pancada", usar_llm=False)
        return caso

    def responder(self, caso: Caso, texto: str) -> Caso:
        if caso.status != "coletando":
            raise CasoEncerrado(f"caso {caso.id} já está {caso.status}")
        caso.historico.append(Mensagem(autor="acs", texto=texto))
        campo = caso.campo_perguntado

        # 1. atualizar_caso: a fala vira campos (LLM validado, ou fallback por palavras)
        novos = self._extrair(caso, texto)
        self._aplicar(caso, novos)

        # 2. rede de segurança: alerta no texto bruto que o LLM deixou passar
        self._rede_seguranca(caso, texto)

        # 3. perguntou demais sem resposta -> pior cenário
        if campo and getattr(caso.campos, campo) is None and caso.tentativas.get(campo, 0) >= MAX_TENTATIVAS:
            valor = PIOR_CENARIO.get(campo, "nao_sei")
            setattr(caso.campos, campo, valor)
            caso.assumidos.append(campo)
            caso.registrar("pior_cenario", "guardrail",
                           entrada={"campo": campo, "tentativas": caso.tentativas[campo]},
                           saida={campo: valor})

        # 4. avaliar_risco: roda a cada turno (sai no vermelho sem terminar a coleta)
        t0 = time.perf_counter()
        cls = classificar(caso.campos, caso.idade)
        caso.registrar("avaliar_risco", "codigo", entrada=self._conhecidos(caso),
                       saida=cls.model_dump(exclude_defaults=True), ms=_ms(t0))

        if cls.cor is not None:
            self._encerrar(caso, cls)
        else:
            self._perguntar(caso, cls.faltando[0])
        return caso

    # ---------- passos ----------

    def _extrair(self, caso: Caso, texto: str) -> dict:
        campo, pergunta = caso.campo_perguntado, caso.ultima_pergunta

        def montar(aviso):
            return prompts.extrair(texto, campo, pergunta, self._conhecidos(caso), aviso)

        rejeitados: dict = {}

        def validar(obj: AcaoAtualizar):
            validos, rej = validar_campos(obj.campos)
            rejeitados.update(rej)
            return validos

        validos = self._chamar(caso, "atualizar_caso", montar, AcaoAtualizar, validar)
        if rejeitados:
            caso.registrar("validar_campos", "guardrail", saida={"rejeitados": rejeitados})
        por_palavras = palavras.extrair(texto, campo)
        if validos is None:
            caso.registrar("fallback_palavras", "guardrail", entrada=texto, saida=por_palavras)
            return por_palavras
        # "pancada" decide o caminho inteiro: se o LLM e as palavras discordam, pergunta de novo.
        if "pancada" in validos and "pancada" in por_palavras and validos["pancada"] != por_palavras["pancada"]:
            caso.registrar("conflito_pancada", "guardrail",
                           saida={"llm": validos["pancada"], "palavras": por_palavras["pancada"]})
            validos = {k: v for k, v in validos.items() if k != "pancada"}
            por_palavras = {k: v for k, v in por_palavras.items() if k != "pancada"}
        # O LLM respondeu, mas rejeitamos um valor ou ele esqueceu o campo perguntado:
        # completa só esses campos com o extrator por palavras.
        faltou = set(rejeitados) | ({campo} if campo and campo not in validos else set())
        complemento = {k: por_palavras[k] for k in faltou if k in por_palavras}
        if complemento:
            validos = {**validos, **complemento}  # cópia: o passo do LLM mostra só o que ele disse
            caso.registrar("complemento_palavras", "guardrail", entrada=texto, saida=complemento)
        return validos

    def _aplicar(self, caso: Caso, novos: dict) -> None:
        ignorados = {}
        for nome, valor in novos.items():
            atual = getattr(caso.campos, nome)
            if atual is None or _piora(nome, atual, valor):
                setattr(caso.campos, nome, valor)
            elif atual != valor:
                ignorados[nome] = {"atual": atual, "proposto": valor}
        if ignorados:
            caso.registrar("nao_baixa_risco", "guardrail", saida={"ignorados": ignorados})

    def _rede_seguranca(self, caso: Caso, texto: str) -> None:
        marcados = {}
        for nome, valor in palavras.alertas_no_texto(texto).items():
            atual = getattr(caso.campos, nome)
            if atual is None or _piora(nome, atual, valor):
                setattr(caso.campos, nome, valor)
                marcados[nome] = valor
        if marcados:
            caso.registrar("rede_seguranca", "guardrail", entrada=texto, saida=marcados)

    def _perguntar(self, caso: Caso, campo: str, usar_llm: bool = True) -> None:
        caso.tentativas[campo] = caso.tentativas.get(campo, 0) + 1
        padrao = PERGUNTAS[campo]
        if caso.tentativas[campo] > 1:
            padrao = "Não entendi. " + padrao
        texto = None
        if usar_llm and self.reescreve_pergunta:
            ultima = next((m.texto for m in reversed(caso.historico) if m.autor == "acs"), None)

            def montar(aviso):
                return prompts.perguntar(campo, padrao, caso.idade, ultima, aviso)

            def validar(obj: AcaoPerguntar):
                if "?" not in obj.texto:
                    raise ValueError("a pergunta precisa terminar com '?'")
                return obj.texto.strip()

            texto = self._chamar(caso, "perguntar", montar, AcaoPerguntar, validar)
        if texto is None:
            texto = padrao
            caso.registrar("pergunta_padrao", "codigo", entrada={"campo": campo}, saida=texto)
        caso.campo_perguntado, caso.ultima_pergunta = campo, texto
        caso.historico.append(Mensagem(autor="agente", texto=texto))

    def _encerrar(self, caso: Caso, cls) -> None:
        caso.status = "finalizado"
        caso.classificacao = cls
        caso.campo_perguntado = None
        motivos = "; ".join(cls.motivos)
        texto = f"Classificação: {NOMES_COR[cls.cor]}. {motivos}."
        if caso.assumidos:
            texto += f" (Pior cenário assumido em: {', '.join(caso.assumidos)}.)"

        # buscar_unidades: destino pelo recurso necessário (código, sem LLM)
        t0 = time.perf_counter()
        try:
            caso.destino = buscar_unidades(cls.recursos, caso.comunidade)
            caso.registrar("buscar_unidades", "codigo",
                           entrada={"recursos": cls.recursos, "comunidade": caso.comunidade},
                           saida=caso.destino.model_dump(exclude_defaults=True), ms=_ms(t0))
            texto += f" {caso.destino.explicacao}"
        except ValueError as e:
            caso.registrar("buscar_unidades", "guardrail", entrada={"comunidade": caso.comunidade},
                           saida={"erro": str(e)})
            texto += " Comunidade não cadastrada: contate a unidade de referência."
        caso.historico.append(Mensagem(autor="agente", texto=texto))
        self._orientar(caso, cls)

    def _orientar(self, caso: Caso, cls) -> None:
        """buscar_protocolo (RAG) -> LLM escreve a fala -> verificador. Sem trecho, sem orientação."""
        t0 = time.perf_counter()
        consulta = orientador.montar_consulta(caso.campos)
        filtro = orientador.filtros(caso.campos)
        try:
            if self._buscador is None:
                from rag.buscar import Buscador
                self._buscador = Buscador()
            candidatos = self._buscador.buscar(consulta, filtro["subtipo"], filtro["condicoes"], k=12)
        except (FileNotFoundError, ValueError) as e:
            caso.registrar("buscar_protocolo", "guardrail", saida={"erro": str(e)}, ms=_ms(t0))
            candidatos = []
        trechos = orientador.escolher(candidatos)
        caso.registrar("buscar_protocolo", "rag",
                       entrada={"consulta": consulta, "subtipo": filtro["subtipo"],
                                "condicoes": sorted(filtro["condicoes"])},
                       saida=[{"id": t["id"], "nota": t["nota"], "tipo": t["tipo"]} for t in trechos], ms=_ms(t0))
        recuperados = [TrechoRecuperado(**{k: t.get(k) for k in TrechoRecuperado.model_fields if k in t})
                       for t in trechos]

        if not trechos:
            caso.orientacao = Orientacao(status="sem_protocolo")
            caso.historico.append(Mensagem(autor="agente",
                                           texto="Sem protocolo para essa situação: contate a unidade."))
            return

        def montar(aviso):
            return prompts.orientar(cls.cor, cls.motivos, trechos, aviso)

        resp = self._chamar(caso, "escrever_orientacao", montar, RespostaOrientar, lambda obj: obj)
        if resp is None:
            caso.orientacao = Orientacao(status="so_trechos", trechos=recuperados,
                                         problemas_verificador=["o modelo não gerou a orientação"])
            return
        if not resp.citacoes:
            resp.citacoes = list(dict.fromkeys(RE_CITACAO.findall(resp.fala)))
        problemas = verificar(resp.fala, resp.citacoes, trechos)
        caso.registrar("verificador", "guardrail" if problemas else "codigo",
                       entrada={"citacoes": resp.citacoes}, saida={"aprovado": not problemas, "problemas": problemas})
        if problemas:
            caso.orientacao = Orientacao(status="so_trechos", trechos=recuperados, problemas_verificador=problemas)
            return
        caso.orientacao = Orientacao(status="ok", fala=resp.fala, citacoes=resp.citacoes, trechos=recuperados)

    # ---------- chamada ao LLM com validação ----------

    def _chamar(self, caso: Caso, ferramenta: str, montar: Callable[[str | None], list[dict]],
                schema: type[BaseModel], validar: Callable[[Any], Any]):
        """Chama o LLM, valida e tenta de novo UMA vez. Devolve None se falhar (o chamador usa o fallback).

        Erro de conexão ou timeout não tem nova tentativa: vai direto para o fallback.
        """
        aviso = None
        for tentativa in (1, 2):
            t0 = time.perf_counter()
            try:
                bruto = self.llm.completar(montar(aviso))
            except Exception as e:  # modelo fora do ar, timeout, não implementado
                caso.registrar(ferramenta, "guardrail", saida={"erro_llm": f"{type(e).__name__}: {e}"[:300]},
                               ms=_ms(t0))
                return None
            try:
                obj = schema.model_validate(extrair_json(bruto))
                resultado = validar(obj)
            except (ValueError, ValidationError) as e:
                erro = str(e).splitlines()[0][:200]
                caso.registrar("validar_json", "guardrail",
                               saida={"tentativa": tentativa, "erro": erro, "resposta": bruto[:300]}, ms=_ms(t0))
                aviso = (f"Sua resposta anterior era inválida ({erro}). "
                         "Responda SOMENTE com o JSON no formato pedido.")
                continue
            caso.registrar(ferramenta, "llm", saida=resultado, ms=_ms(t0))
            return resultado
        return None

    @staticmethod
    def _conhecidos(caso: Caso) -> dict:
        return caso.campos.model_dump(exclude_none=True)


def _ms(t0: float) -> int:
    return int((time.perf_counter() - t0) * 1000)
