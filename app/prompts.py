"""Prompts do agente. Ajuste aqui depois de rodar scripts/testar_modelo.py.

Contrato: a mensagem do usuário é sempre um JSON com "tarefa" (ver app/llm/base.py).
"""
from __future__ import annotations
import json

DESCRICAO_CAMPOS = {
    "pancada": "true se teve pancada, queda ou batida; false se a mancha apareceu sozinha",
    "local": "onde fica o hematoma: cabeca | torax | barriga | braco | perna",
    "mecanismo": "como foi a pancada: queda_altura | acidente_barco | acidente_motor | pancada_leve | outro",
    "sinais_cabeca": "vômito, sonolência ou confusão depois de pancada na cabeça",
    "dor_forte_ou_falta_ar": "dor forte na barriga ou falta de ar depois do trauma",
    "deformidade": "membro torto, frio ou azulado",
    "mexe_apoia": "consegue mexer e apoiar o braço ou a perna",
    "crescendo": "a própria mancha roxa está aumentando rápido",
    "sangramento_nao_para": "um corte ou ferida que não para de sangrar (sangue na gengiva, nariz ou xixi NÃO conta aqui: é sangramento_mucosa)",
    "febre": "febre nos últimos dias",
    "sangramento_mucosa": "sangramento na gengiva, no nariz ou na urina",
    "petequias": "pontinhos vermelhos na pele",
    "picada_cobra": "picada de cobra recente",
    "cansaco_palidez": "cansaço fora do normal ou palidez",
    "anticoagulante": "usa AAS, Melhoral ou remédio para afinar o sangue",
}

SISTEMA_EXTRAIR = """Você ajuda um Agente Comunitário de Saúde (ACS) na triagem de um hematoma (mancha roxa).
Sua tarefa: transformar a fala do ACS em campos do caso.

Responda SOMENTE com um JSON neste formato:
{"acao": "atualizar_caso", "campos": {"nome_do_campo": valor}}

Regras:
- Use só os campos do "esquema". Campos de sim/não recebem SOMENTE true, false ou "nao_sei"
  (nunca o nome de um remédio ou outro texto: "toma AAS" vira "anticoagulante": true).
- "local" e "mecanismo" só aceitam os valores listados no esquema.
- Preencha só o que a fala diz. Não adivinhe. Campo não mencionado fica de fora.
- Se o ACS responde "sim", "não" ou "não sei" à pergunta feita, preencha o "campo_perguntado".
- O ACS fala de modo informal: "roxo" = hematoma, "Melhoral" = AAS, "golfou" = vomitou.

Exemplo 1
fala_acs: "caiu do açaizeiro e bateu a cabeça, vomitou duas vez"
{"acao": "atualizar_caso", "campos": {"pancada": true, "local": "cabeca", "mecanismo": "queda_altura", "sinais_cabeca": true}}

Exemplo 2
campo_perguntado: "febre"; fala_acs: "não, febre não teve"
{"acao": "atualizar_caso", "campos": {"febre": false}}

Exemplo 3
fala_acs: "surgiu um roxo na coxa do nada, ninguém bateu, e o nariz tá sangrando"
{"acao": "atualizar_caso", "campos": {"pancada": false, "local": "perna", "sangramento_mucosa": true}}"""

SISTEMA_PERGUNTAR = """Você ajuda um Agente Comunitário de Saúde (ACS) na triagem de um hematoma.
Reescreva a pergunta padrão para o ACS em português simples e curto.
Faça UMA pergunta só, sobre o campo indicado, com o mesmo sentido da pergunta padrão
(um "sim" do ACS tem que querer dizer a mesma coisa).
Não dê diagnóstico nem orientação.

Responda SOMENTE com um JSON: {"acao": "perguntar", "texto": "..."}"""


SISTEMA_ORIENTAR = """Você ajuda um Agente Comunitário de Saúde (ACS) a orientar a família de uma pessoa com hematoma.
Escreva uma orientação curta, em português simples, usando SOMENTE os trechos do protocolo fornecidos.

Regras:
- TODA frase termina com o id do trecho entre colchetes, ex.: [dengue_nao_fazer_01]. Frase sem id é recusada.
- Não escreva frase que não venha de um trecho (nada de conclusão, resumo ou despedida).
- Não acrescente remédio, dose, exame ou conduta que não esteja nos trechos.
- Comece pelo que fazer agora; depois o que não fazer; depois quando procurar ajuda.
- No máximo 5 frases. Não repita o destino nem a cor.

Exemplo (trechos: gelo_01 = "Aplicar compressa fria ou gelo envolto em pano por 15 a 20 minutos.",
massagem_01 = "Não massagear o local.", voltar_01 = "Procurar a unidade se o hematoma aumentar ou a dor piorar."):
{"fala": "Coloque gelo enrolado em um pano no roxo por 15 a 20 minutos [gelo_01]. Não massageie o local [massagem_01]. Procure a unidade se o roxo aumentar ou a dor piorar [voltar_01].", "citacoes": ["gelo_01", "massagem_01", "voltar_01"]}

Responda SOMENTE com um JSON: {"fala": "...", "citacoes": ["id1", "id2"]}"""


def _json(d: dict) -> str:
    return json.dumps(d, ensure_ascii=False)


def extrair(fala_acs: str, campo_perguntado: str | None, pergunta: str | None,
            campos_conhecidos: dict, aviso: str | None = None) -> list[dict]:
    pedido = {
        "tarefa": "extrair",
        "pergunta_feita": pergunta,
        "campo_perguntado": campo_perguntado,
        "fala_acs": fala_acs,
        "campos_conhecidos": campos_conhecidos,
        "esquema": DESCRICAO_CAMPOS,
    }
    if aviso:
        pedido["aviso"] = aviso
    return [{"role": "system", "content": SISTEMA_EXTRAIR}, {"role": "user", "content": _json(pedido)}]


def perguntar(campo: str, pergunta_padrao: str, idade: int | None, ultima_fala_acs: str | None,
              aviso: str | None = None) -> list[dict]:
    pedido = {
        "tarefa": "perguntar",
        "campo": campo,
        "descricao_campo": DESCRICAO_CAMPOS.get(campo, ""),
        "pergunta_padrao": pergunta_padrao,
        "idade": idade,
        "ultima_fala_acs": ultima_fala_acs,
    }
    if aviso:
        pedido["aviso"] = aviso
    return [{"role": "system", "content": SISTEMA_PERGUNTAR}, {"role": "user", "content": _json(pedido)}]


def orientar(cor: str, motivos: list[str], trechos: list[dict], aviso: str | None = None) -> list[dict]:
    pedido = {
        "tarefa": "orientar",
        "cor": cor,
        "motivos": motivos,
        "trechos": [{"id": t["id"], "texto": t["texto"]} for t in trechos],
    }
    if aviso:
        pedido["aviso"] = aviso
        
    sistema = SISTEMA_ORIENTAR
    sistema += f"\n\nO risco calculado para este paciente é {cor.upper()}. REGRA ABSOLUTA: Se o risco for VERMELHO ou LARANJA, é estritamente proibido aconselhar o paciente a ficar em observação em casa ou aguardar revisita. Use APENAS os trechos fornecidos que condizem com uma emergência médica."
    
    return [{"role": "system", "content": sistema}, {"role": "user", "content": _json(pedido)}]
