"""Schemas Pydantic: o caso, as respostas do LLM e o resultado da triagem.

Tudo que vem do LLM passa por um destes modelos antes de ser usado.
"""
from __future__ import annotations
from datetime import datetime
from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

NaoSei = Literal["nao_sei"]
# None = ainda não perguntado; "nao_sei" = o ACS não sabe (as regras tratam como SIM: pior cenário).
SimNao = Optional[Union[bool, NaoSei]]

Local = Literal["cabeca", "torax", "barriga", "braco", "perna"]
Mecanismo = Literal["queda_altura", "acidente_barco", "acidente_motor", "pancada_leve", "outro"]
Cor = Literal["vermelho", "laranja", "amarelo", "verde"]
Quem = Literal["llm", "codigo", "rag", "guardrail", "pessoa"]


class CamposCaso(BaseModel):
    """Campos clínicos do caso. É o que o LLM preenche e o que as regras leem."""

    model_config = ConfigDict(extra="ignore")

    pancada: Optional[bool] = None
    # caminho trauma
    local: Optional[Local] = None
    mecanismo: Optional[Mecanismo] = None
    sinais_cabeca: SimNao = None  # vômito, sonolência ou confusão após pancada na cabeça
    dor_forte_ou_falta_ar: SimNao = None  # após trauma em tórax ou barriga
    deformidade: SimNao = None  # membro torto, frio ou azulado
    mexe_apoia: SimNao = None  # consegue mexer e apoiar o membro
    # caminho doença (sem pancada)
    febre: SimNao = None
    sangramento_mucosa: SimNao = None  # gengiva, nariz ou urina
    petequias: SimNao = None  # pontinhos vermelhos na pele
    picada_cobra: SimNao = None
    cansaco_palidez: SimNao = None
    # comuns aos dois caminhos
    crescendo: SimNao = None  # a mancha roxa está aumentando rápido (perguntado)
    sangramento_nao_para: SimNao = None  # corte/ferida que não para de sangrar (só se o ACS falar)
    anticoagulante: SimNao = None  # AAS ou remédio para afinar o sangue


# ---------- respostas do LLM (validadas) ----------

class AcaoAtualizar(BaseModel):
    acao: Literal["atualizar_caso"]
    campos: dict[str, Any]


class AcaoPerguntar(BaseModel):
    acao: Literal["perguntar"]
    texto: str = Field(min_length=5, max_length=220)


class RespostaOrientar(BaseModel):
    fala: str = Field(min_length=10, max_length=1200)
    citacoes: list[str] = []  # se vier vazio, usamos os [ids] citados dentro da fala


# ---------- resultado ----------

class Passo(BaseModel):
    """Um passo do agente, mostrado no painel de raciocínio."""

    n: int
    ferramenta: str
    quem: Quem
    entrada: Any = None
    saida: Any = None
    ms: int = 0


class Classificacao(BaseModel):
    cor: Optional[Cor] = None  # None = ainda faltam campos e não há alerta
    motivos: list[str] = []
    recursos: list[str] = []  # recursos que o destino precisa ter
    faltando: list[str] = []
    alerta: bool = False


class Destino(BaseModel):
    em_casa: bool = False
    unidade_id: Optional[str] = None
    nome: Optional[str] = None
    tempo_barco_min: Optional[int] = None
    recursos_atendidos: list[str] = []
    recursos_faltando: list[str] = []  # só se nenhuma unidade tiver tudo
    explicacao: str = ""


class TrechoRecuperado(BaseModel):
    id: str
    tipo: str
    texto: str
    fonte: str
    fonte_titulo: str
    pagina: Optional[int] = None
    origem: str = "auto"  # "curado" | "auto"
    conferido: bool = True  # texto achado na página citada do PDF
    nota: float


class Orientacao(BaseModel):
    status: Literal["ok", "so_trechos", "sem_protocolo"]
    fala: Optional[str] = None
    citacoes: list[str] = []
    trechos: list[TrechoRecuperado] = []
    problemas_verificador: list[str] = []


class Resultado(BaseModel):
    cor: Cor
    motivos: list[str]
    recursos: list[str]
    assumidos: list[str] = []  # campos em que o agente assumiu o pior cenário
    destino: Destino
    orientacao: Orientacao


class Mensagem(BaseModel):
    autor: Literal["agente", "acs", "sistema"]
    texto: str


class Caso(BaseModel):
    id: str
    criado_em: datetime
    idade: Optional[int] = None
    comunidade: str
    campos: CamposCaso = CamposCaso()
    status: Literal["coletando", "finalizado", "confirmado"] = "coletando"
    campo_perguntado: Optional[str] = None
    ultima_pergunta: Optional[str] = None
    tentativas: dict[str, int] = {}
    assumidos: list[str] = []
    historico: list[Mensagem] = []
    passos: list[Passo] = []
    foto: Optional[str] = None
    classificacao: Optional[Classificacao] = None
    destino: Optional[Destino] = None
    orientacao: Optional[Orientacao] = None
    resultado: Optional[Resultado] = None
    ficha_id: Optional[int] = None

    def registrar(self, ferramenta: str, quem: Quem, entrada: Any = None, saida: Any = None, ms: int = 0) -> None:
        self.passos.append(
            Passo(n=len(self.passos) + 1, ferramenta=ferramenta, quem=quem, entrada=entrada, saida=saida, ms=ms)
        )


# ---------- entradas da API ----------

class NovoCaso(BaseModel):
    idade: Optional[int] = Field(default=None, ge=0, le=120)
    comunidade: str = Field(min_length=2, max_length=80)


class NovaMensagem(BaseModel):
    texto: str = Field(min_length=1, max_length=1000)


class NovaFoto(BaseModel):
    imagem: str  # data URL base64 (data:image/jpeg;base64,...)


class EstadoSinal(BaseModel):
    ligado: bool
