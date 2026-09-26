"""Regras de risco em código puro: sinais de alerta, cor, motivo e campos que faltam.

O LLM NUNCA decide a cor. Estas funções são determinísticas e testadas pelo avaliacao/avaliar.py.

Vermelho e verde seguem o plano técnico. Laranja e amarelo são uma PROPOSTA
para a equipe validar (ver comentários "PROPOSTA").
"""
from __future__ import annotations
from app.modelos import CamposCaso, Classificacao

ORDEM_COR = {"verde": 0, "amarelo": 1, "laranja": 2, "vermelho": 3}

# Campos que, uma vez SIM (ou "nao_sei"), o LLM não consegue mais trocar para NÃO.
CAMPOS_ALERTA = {
    "sinais_cabeca", "dor_forte_ou_falta_ar", "deformidade", "crescendo_ou_sangrando",
    "febre", "sangramento_mucosa", "petequias", "picada_cobra", "cansaco_palidez", "anticoagulante",
}

# Valor usado quando o campo foi perguntado MAX_TENTATIVAS vezes sem resposta.
PIOR_CENARIO = {
    "pancada": True,
    "local": "cabeca",
    "mecanismo": "queda_altura",
}  # campos sim/não não listados aqui viram "nao_sei" (tratado como SIM)

PERGUNTAS = {
    "pancada": "Conte o que aconteceu. Teve pancada ou queda?",
    "local": "Onde fica o hematoma: cabeça, peito, barriga, braço ou perna?",
    "mecanismo": "Como foi a pancada: queda de altura, acidente de barco ou de moto, ou uma pancada leve?",
    "sinais_cabeca": "Depois da pancada na cabeça, teve vômito, sonolência ou confusão?",
    "dor_forte_ou_falta_ar": "Está com dor forte na barriga ou falta de ar?",
    "deformidade": "O braço ou a perna ficou torto, frio ou com cor azulada?",
    "mexe_apoia": "Consegue mexer e apoiar o braço ou a perna?",
    "crescendo_ou_sangrando": "O hematoma está crescendo rápido ou tem algum sangramento que não para?",
    "febre": "Teve febre nos últimos dias?",
    "sangramento_mucosa": "Tem sangramento na gengiva, no nariz ou na urina?",
    "petequias": "Apareceram pontinhos vermelhos na pele?",
    "picada_cobra": "Teve picada de cobra recente?",
    "cansaco_palidez": "Está com cansaço fora do normal ou pálida?",
    "anticoagulante": "Usa AAS, Melhoral ou algum remédio para afinar o sangue?",
}


def sim(valor) -> bool:
    """SIM ou 'não sei' contam como SIM: na dúvida, pior cenário."""
    return valor is True or valor == "nao_sei"


def subtipo(c: CamposCaso) -> str | None:
    if c.pancada is None:
        return None
    return "traumatico" if c.pancada else "espontaneo"


def campos_necessarios(c: CamposCaso) -> list[str]:
    """Campos na ordem em que o agente pergunta. Sinais de alerta vêm primeiro."""
    if c.pancada is None:
        return ["pancada"]
    if c.pancada:
        ordem = ["local"]
        if c.local == "cabeca":
            ordem.append("sinais_cabeca")
        if c.local in ("torax", "barriga"):
            ordem.append("dor_forte_ou_falta_ar")
        ordem.append("crescendo_ou_sangrando")
        if c.local in ("braco", "perna"):
            ordem += ["deformidade", "mexe_apoia"]
        ordem += ["mecanismo", "anticoagulante"]
        return ordem
    return [
        "picada_cobra", "febre", "sangramento_mucosa", "crescendo_ou_sangrando",
        "petequias", "cansaco_palidez", "anticoagulante",
    ]


def campos_faltando(c: CamposCaso) -> list[str]:
    return [f for f in campos_necessarios(c) if getattr(c, f) is None]


def sinais_de_alerta(c: CamposCaso) -> list[tuple[str, list[str]]]:
    """Sinais de alerta fixos do plano técnico. Qualquer um => vermelho, sem passar pelo LLM.

    Roda a CADA turno, com o caso incompleto, para sair na hora.
    """
    alertas: list[tuple[str, list[str]]] = []
    trauma = c.pancada is True
    espontaneo = c.pancada is False
    if trauma and c.local == "cabeca" and sim(c.sinais_cabeca):
        alertas.append(("Vômito, sonolência ou confusão após pancada na cabeça", ["tomografia"]))
    if trauma and c.local in ("torax", "barriga") and sim(c.dor_forte_ou_falta_ar):
        alertas.append(("Dor forte na barriga ou falta de ar após trauma", ["tomografia", "centro_cirurgico"]))
    if trauma and c.local in ("braco", "perna") and (sim(c.deformidade) or c.mexe_apoia is False or c.mexe_apoia == "nao_sei"):
        alertas.append(("Membro deformado, frio ou sem movimento", ["raio_x"]))
    if espontaneo and sim(c.febre) and sim(c.sangramento_mucosa):
        alertas.append((
            "Manchas espontâneas com febre e sangramento de mucosa (sinal de alarme de dengue)",
            ["exame_sangue", "hidratacao_venosa"],
        ))
    if sim(c.picada_cobra):
        alertas.append(("Hematoma depois de picada de cobra", ["soro_antiofidico"]))
    # por último: é o alerta mais genérico, os específicos aparecem primeiro como motivo
    if sim(c.crescendo_ou_sangrando):
        # com trauma: pode ser sangramento interno (cirurgia); sem trauma: investigar coagulação (exame de sangue)
        alertas.append(("Hematoma crescendo rápido ou sangramento que não para",
                        ["exame_sangue", "centro_cirurgico"] if trauma else ["exame_sangue"]))
    return alertas


def _criterios_sem_alerta(c: CamposCaso, idade: int | None) -> list[tuple[str, str, list[str]]]:
    """(cor, motivo, recursos) para caso completo e sem sinal de alerta."""
    crit: list[tuple[str, str, list[str]]] = []
    if c.pancada:
        tronco_ou_cabeca = c.local in ("cabeca", "torax", "barriga")
        # PROPOSTA laranja: mecanismo de alta energia
        if c.mecanismo in ("queda_altura", "acidente_barco", "acidente_motor"):
            crit.append(("laranja", "Pancada forte (queda de altura, barco ou moto)",
                         ["tomografia"] if tronco_ou_cabeca else ["raio_x"]))
        if c.local == "cabeca" and sim(c.anticoagulante):
            crit.append(("laranja", "Pancada na cabeça em quem usa remédio que afina o sangue", ["tomografia"]))
        if c.local == "cabeca" and idade is not None and idade >= 65:
            crit.append(("laranja", "Pancada na cabeça em pessoa idosa", ["tomografia"]))
        # PROPOSTA amarelo
        if c.local == "cabeca":
            crit.append(("amarelo", "Pancada na cabeça sem sinal de alerta: precisa de avaliação", ["consulta"]))
        if c.local in ("torax", "barriga"):
            crit.append(("amarelo", "Pancada no tronco sem sinal de alerta: precisa de avaliação", ["consulta"]))
        if sim(c.anticoagulante):
            crit.append(("amarelo", "Usa remédio que afina o sangue", ["consulta"]))
        if not crit:
            crit.append(("verde", "Pancada leve em braço ou perna, mexe normal, sem sinal de alerta", []))
        return crit

    # sem pancada (espontâneo)
    if sim(c.febre):
        crit.append(("laranja", "Mancha roxa sem pancada e com febre: suspeita de dengue",
                     ["exame_sangue", "hidratacao_venosa"]))
    if sim(c.sangramento_mucosa) or sim(c.petequias):
        crit.append(("laranja", "Sangramento ou pontinhos vermelhos sem causa aparente", ["exame_sangue"]))
    if sim(c.cansaco_palidez):
        crit.append(("amarelo", "Mancha roxa sem pancada com cansaço ou palidez", ["exame_sangue"]))
    if sim(c.anticoagulante):
        crit.append(("amarelo", "Mancha roxa sem pancada em quem usa remédio que afina o sangue", ["consulta"]))
    if not crit:
        crit.append(("amarelo", "Mancha roxa sem pancada: precisa de avaliação na unidade", ["consulta"]))
    return crit


def classificar(c: CamposCaso, idade: int | None = None) -> Classificacao:
    """avaliar_risco: cor + motivo + recursos + campos que faltam."""
    faltando = campos_faltando(c)
    alertas = sinais_de_alerta(c)
    if alertas:
        recursos: list[str] = []
        for _, rec in alertas:
            recursos += [r for r in rec if r not in recursos]
        return Classificacao(cor="vermelho", motivos=[m for m, _ in alertas], recursos=recursos,
                             faltando=faltando, alerta=True)
    if faltando:
        return Classificacao(cor=None, faltando=faltando)

    crit = _criterios_sem_alerta(c, idade)
    cor = max((cr[0] for cr in crit), key=ORDEM_COR.__getitem__)
    motivos, recursos = [], []
    for cr_cor, motivo, rec in crit:
        if cr_cor == cor:
            motivos.append(motivo)
            recursos += [r for r in rec if r not in recursos]
    return Classificacao(cor=cor, motivos=motivos, recursos=recursos)


def condicoes(c: CamposCaso) -> set[str]:
    """Metadados do caso usados para filtrar os trechos do protocolo (não a pergunta livre)."""
    s: set[str] = set()
    if c.pancada is True:
        if c.local == "cabeca":
            s.add("cabeca")
        elif c.local in ("torax", "barriga"):
            s.add("tronco")
        elif c.local in ("braco", "perna"):
            s.add("membro")
    if c.pancada is False and sim(c.febre):
        s.add("dengue")
    if sim(c.picada_cobra):
        s.add("cobra")
    if sim(c.anticoagulante):
        s.add("anticoagulante")
    return s
