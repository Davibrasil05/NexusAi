"""Extrator de campos por palavras-chave, sem LLM.

Três usos:
1. É o "cérebro" do LLM simulado (app/llm/mock.py), para o time trabalhar sem o modelo.
2. É o fallback quando o LLM devolve JSON inválido duas vezes.
3. É a REDE DE SEGURANÇA: depois do LLM, procura sinais de alerta no texto bruto do ACS.
   Se achar um alerta que o LLM deixou passar, marca o campo (pior cenário).
"""
from __future__ import annotations
import re

from unidecode import unidecode

from app.regras import CAMPOS_ALERTA

NEGACOES = {"nao", "nem", "sem", "nenhum", "nenhuma", "nunca"}
JANELA_NEGACAO = 3  # palavras antes do termo
# A negação não atravessa vírgula/ponto nem estas palavras: "sem pancada, febre" -> febre é SIM.
SEPARADOR = "|"
BARREIRAS = {SEPARADOR, "mas", "e", "porem", "so", "que"}

# "neg" = frases que significam NÃO (checadas antes); "pos" = termos que significam SIM.
# Os padrões são regex aplicadas a texto normalizado (minúsculo, sem acento), com \b no início.
LEXICO_BOOL: dict[str, dict[str, list[str]]] = {
    "pancada": {
        "neg": [r"sem (pancada|queda|batida)", r"nao (teve|houve|levou) (pancada|queda|batida)",
                r"nao (bateu|bati|caiu|cai|machucou|machuquei|levou pancada)", r"sem bater", r"sozinh", r"do nada", r"espontane", r"sem motivo"],
        "pos": [r"pancada", r"bateu", r"bati\b", r"caiu", r"cai\b", r"queda", r"tombo", r"batida", r"acidente",
                r"machucou", r"levou uma", r"trombou", r"esbarr", r"topada"],
    },
    "sinais_cabeca": {
        "neg": [],
        "pos": [r"vomit", r"golf", r"sonolen", r"muito sono", r"dormindo muito", r"confus", r"desmai",
                r"desacord", r"apagou", r"nao acorda", r"variando", r"moleza"],
    },
    "dor_forte_ou_falta_ar": {
        "neg": [],
        "pos": [r"falta de ar", r"faltando ar", r"sem ar\b", r"dificuldade (pra|para|de) respirar",
                r"nao consegue respirar", r"dor forte", r"muita dor", r"dor muito forte", r"barriga dura"],
    },
    "deformidade": {
        "neg": [],
        "pos": [r"tort[oa]?\b", r"entort", r"deformad", r"osso (pra|para) fora", r"fora do lugar",
                r"fri[oa]\b", r"gelad", r"azulad"],
    },
    "mexe_apoia": {
        "neg": [r"nao (consegue|pode|quer) (mexer|apoiar|pisar|andar|firmar)", r"nao mexe", r"nao apoia",
                r"nao pisa", r"nao anda", r"sem movimento"],
        "pos": [r"mexe", r"apoia", r"pisa\b", r"anda (normal|bem)", r"consegue (mexer|andar|apoiar|pisar)",
                r"movimenta"],
    },
    "crescendo": {
        "neg": [r"mesmo tamanho", r"nao (cresceu|aumentou|esta crescendo|ta crescendo|esta aumentando|ta aumentando)"],
        "pos": [r"crescendo", r"cresceu", r"aumentando", r"aumentou", r"inchando (rapido|muito)", r"so aumenta",
                r"espalhando"],
    },
    "sangramento_nao_para": {
        "neg": [],
        "pos": [r"nao para de sangrar", r"sangrando muito", r"sangue nao para", r"sangramento que nao para",
                r"jorrando", r"sangrando sem parar"],
    },
    "febre": {
        "neg": [],
        "pos": [r"febr[ei]", r"febril", r"(ta|esta|corpo) quente", r"quentura"],
    },
    "sangramento_mucosa": {
        "neg": [],
        "pos": [r"gengiva", r"sangr\w* (pelo|no|do) nariz", r"nariz sangr", r"sangue (no|do|pelo) nariz",
                r"sangue na (urina|xixi)", r"(urina|xixi)\b[\w\s]{0,20}\bsangue", r"(urina|xixi) (vermelh|escur)",
                r"sangue na boca", r"epistax", r"mucosa"],
    },
    "petequias": {
        "neg": [],
        "pos": [r"pontinhos", r"pintinhas", r"pintas vermelhas", r"petequia", r"pontos vermelhos",
                r"bolinhas vermelhas"],
    },
    "picada_cobra": {
        "neg": [],
        "pos": [r"cobra", r"jararaca", r"surucucu", r"cascavel", r"ofidi", r"serpente"],
    },
    "cansaco_palidez": {
        "neg": [],
        "pos": [r"cansa", r"palid", r"descorad", r"fraqueza", r"fraca\b", r"fraco\b", r"sem cor",
                r"branquel"],
    },
    "anticoagulante": {
        "neg": [],
        "pos": [r"aas\b", r"melhoral", r"aspirina", r"afina\w* o sangue", r"varfarina", r"marevan",
                r"anticoagul", r"clopidogrel", r"rivaroxab", r"xarelto", r"apixab", r"eliquis"],
    },
}

LEXICO_CATEGORIA: dict[str, dict[str, list[str]]] = {
    "local": {
        "cabeca": [r"cabeca", r"testa", r"nuca", r"cranio", r"rosto", r"olho", r"cara\b"],
        "torax": [r"peito", r"torax", r"costela"],
        "barriga": [r"barriga", r"abdom", r"bucho", r"estomago"],
        "braco": [r"braco", r"maos?\b", r"cotovelo", r"ombro", r"punho", r"dedo"],
        "perna": [r"perna", r"canela", r"joelho", r"coxa", r"pes?\b", r"tornozelo"],
    },
    "mecanismo": {
        "pancada_leve": [r"leve\b", r"pancadinha", r"esbarr", r"topada",
                         r"bateu (a \w+ )?n[oa] (mesa|porta|cadeira|banco|parede|quina|cama)", r"brincando"],
        "acidente_barco": [r"barco", r"canoa", r"rabeta", r"voadeira", r"lancha", r"batelao"],
        "acidente_motor": [r"moto\b", r"motocicleta", r"carro", r"atropel"],
        "outro": [r"outro jeito", r"de outro jeito", r"outra coisa"],
        "queda_altura": [r"altura", r"escada", r"telhado", r"acaizeiro", r"arvore", r"jirau", r"palafita",
                         r"trapiche", r"ponte", r"caiu d[oa] alto"],
    },
}

RE_NAO_SEI = re.compile(r"\b(nao sei|sei nao|sei la|nao lembro|nao tenho certeza|nao sabe|talvez)\b")
RE_SIM = re.compile(r"^(sim|s|tem|teve|foi|isso|positivo|uhum|aham|claro|verdade|com certeza)\b")
RE_NAO = re.compile(r"^(nao|n|nada|nenhum|nenhuma|negativo|nunca)\b")


def normalizar(texto: str) -> str:
    t = unidecode(texto).lower()
    t = re.sub(r"[,.;:!?]+", f" {SEPARADOR} ", t)  # fim de ideia vira separador
    t = re.sub(r"[^\w\s|]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _negado(t: str, inicio: int) -> bool | str:
    """True se há negação logo antes; 'nao_sei' se há 'não sei' logo antes."""
    antes = []
    for p in reversed(t[:inicio].split()):
        if p in BARREIRAS:
            break
        antes.insert(0, p)
    antes = antes[-JANELA_NEGACAO - 1:]
    if RE_NAO_SEI.search(" ".join(antes)):
        return "nao_sei"
    return any(p in NEGACOES for p in antes[-JANELA_NEGACAO:])


# Negação DEPOIS do termo, comum no Norte: "febre não", "vomitou não", "febre não teve".
# Só conta se a frase acaba ali ou segue um destes verbos; "febre não passa" continua SIM.
NEGA_DEPOIS = {"nao", "nunca", "nenhum", "nenhuma"}
VERBOS_DEPOIS = {"teve", "tem", "ta", "esta", "houve", "deu", "sentiu", "apresentou", "apareceu", "viu", "vi",
                 "senhor", "senhora", "doutor", "doutora"}


def _negado_depois(t: str, fim: int) -> bool | str:
    resto = re.sub(r"^\w*", "", t[fim:]).split()  # termina a palavra do termo ("vomit" -> "vomitou")
    if not resto or resto[0] not in NEGA_DEPOIS:
        return False
    seguinte = resto[1] if len(resto) > 1 else None
    if seguinte == "sei":
        return "nao_sei"
    return seguinte is None or seguinte in BARREIRAS or seguinte in VERBOS_DEPOIS


def _detectar_bool(t: str, lex: dict[str, list[str]]):
    for p in lex["neg"]:
        if re.search(r"\b" + p, t):
            return False
    # Olha TODAS as menções: qualquer uma afirmada vence (na dúvida, pior cenário).
    achou_negado = achou_nao_sei = False
    for p in lex["pos"]:
        for m in re.finditer(r"\b" + p, t):
            neg = _negado(t, m.start()) or _negado_depois(t, m.end())
            if neg == "nao_sei":
                achou_nao_sei = True
            elif neg:
                achou_negado = True
            else:
                return True
    if achou_nao_sei:
        return "nao_sei"
    return False if achou_negado else None


def _detectar_categoria(t: str, valores: dict[str, list[str]]):
    melhor = None  # (posição, valor)
    for valor, padroes in valores.items():
        for p in padroes:
            m = re.search(r"\b" + p, t)
            if m and (melhor is None or m.start() < melhor[0]):
                melhor = (m.start(), valor)
    return melhor[1] if melhor else None


def resposta_curta(t: str):
    """Interpreta 'sim', 'não', 'não sei' como resposta à pergunta feita."""
    if RE_NAO_SEI.search(t):
        return "nao_sei"
    if RE_SIM.match(t):
        return True
    if RE_NAO.match(t):
        return False
    return None


def extrair(texto: str, campo_perguntado: str | None = None) -> dict:
    """Devolve os campos que a fala do ACS menciona."""
    t = normalizar(texto)
    campos: dict = {}
    for campo, lex in LEXICO_BOOL.items():
        v = _detectar_bool(t, lex)
        if v is not None:
            campos[campo] = v
    for campo, valores in LEXICO_CATEGORIA.items():
        v = _detectar_categoria(t, valores)
        if v is not None:
            campos[campo] = v
    if campo_perguntado and campo_perguntado not in campos:
        r = resposta_curta(t)
        if r is not None and campo_perguntado in LEXICO_BOOL:
            if not (campo_perguntado == "pancada" and r == "nao_sei"):
                campos[campo_perguntado] = r
    return campos


def alertas_no_texto(texto: str) -> dict:
    """Rede de segurança: só os campos de alerta marcados como SIM ou 'não sei' no texto bruto."""
    t = normalizar(texto)
    achados = {}
    for campo in CAMPOS_ALERTA:
        v = _detectar_bool(t, LEXICO_BOOL[campo])
        if v is True or v == "nao_sei":
            achados[campo] = v
    # "mexe_apoia" é o único alerta invertido: NÃO mexer é o sinal.
    if _detectar_bool(t, LEXICO_BOOL["mexe_apoia"]) is False:
        achados["mexe_apoia"] = False
    return achados
