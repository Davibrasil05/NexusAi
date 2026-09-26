"""buscar_protocolo: monta a busca a partir do CASO (não de pergunta livre) e escolhe os trechos.

A escolha pega o melhor trecho de cada tipo (o que fazer, o que não fazer, sinais de alerta,
quando voltar) e completa pela nota, até RAG_TOP_K.
"""
from __future__ import annotations
from app.config import RAG_TOP_K
from app.modelos import CamposCaso
from app.regras import condicoes, sim, subtipo

BASE = "hematoma equimose mancha roxa"
TERMOS = {
    "sinais_cabeca": "vomito sonolencia confusao traumatismo cranioencefalico",
    "dor_forte_ou_falta_ar": "dor abdominal falta de ar trauma toracico abdominal lesao interna",
    "deformidade": "fratura deformidade imobilizar",
    "crescendo_ou_sangrando": "sangramento hemorragia compressao",
    "febre": "febre dengue hidratacao",
    "sangramento_mucosa": "sangramento gengiva nariz mucosa sinais de alarme",
    "petequias": "petequias manchas vermelhas",
    "picada_cobra": "picada cobra serpente acidente ofidico soro antiofidico",
    "cansaco_palidez": "palidez cansaco anemia",
    "anticoagulante": "anticoagulante acido acetilsalicilico aas",
}
LOCAIS = {
    "cabeca": "cabeca traumatismo craniano",
    "torax": "torax trauma",
    "barriga": "abdome trauma",
    "braco": "membro superior braco fratura gelo compressa",
    "perna": "membro inferior perna fratura gelo compressa",
}
ORDEM_TIPOS = ["primeiros_cuidados", "nao_fazer", "sinais_de_alerta", "quando_voltar"]


def montar_consulta(c: CamposCaso, falas_acs: str = "") -> str:
    """Termos do caso + o que o ACS falou (ex.: "amarelado", "antigo"). Só ORDENA: o filtro vem do caso."""
    partes = [BASE, falas_acs]
    if c.pancada and c.local:
        partes.append(LOCAIS[c.local])
    for campo, termos in TERMOS.items():
        if sim(getattr(c, campo)):
            partes.append(termos)
    if c.mexe_apoia is False or c.mexe_apoia == "nao_sei":
        partes.append(TERMOS["deformidade"])
    return " ".join(partes)


def filtros(c: CamposCaso) -> dict:
    return {"subtipo": subtipo(c), "condicoes": condicoes(c)}


def escolher(candidatos: list[dict], k: int = RAG_TOP_K) -> list[dict]:
    escolhidos = []
    for tipo in ORDEM_TIPOS:
        melhor = next((t for t in candidatos if t["tipo"] == tipo), None)
        if melhor:
            escolhidos.append(melhor)
    for t in candidatos:
        if len(escolhidos) >= k:
            break
        if t not in escolhidos:
            escolhidos.append(t)
    return sorted(escolhidos[:k], key=lambda t: t["nota"], reverse=True)
