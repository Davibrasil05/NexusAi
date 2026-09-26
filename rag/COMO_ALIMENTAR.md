# Como alimentar o RAG

O RAG é a memória de protocolos do agente. Ele **nunca inventa conduta**: toda orientação
sai de um trecho que está aqui, com fonte e página. Quanto mais conteúdo bom entrar, mais
situações o agente consegue orientar.

> Pode colocar muito conteúdo. A busca (BM25) procura em milhares de trechos em milissegundos,
> e só os 3 a 5 melhores vão para o modelo. O que atrapalha é conteúdo **fora do assunto**
> (sumário, referências, anexos administrativos), porque ele gera falsos resultados.

## Preparar (uma vez)

```bash
cd triagem-acs
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Os 3 jeitos de adicionar conteúdo

### 1. Jogar o documento inteiro (rápido, volume)

1. Coloque o PDF (ou `.txt`/`.md`) em `rag/docs/`.
2. Cadastre em `rag/fontes.json` (se esquecer, entra sozinho como `geral`, com aviso):

```json
{
  "id": "dengue_manejo",
  "titulo": "Dengue: diagnóstico e manejo clínico – Ministério da Saúde",
  "arquivo": "dengue_manejo.pdf",
  "url": "link oficial de onde baixou",
  "padrao": { "subtipo": "espontaneo", "condicao": "dengue" },
  "ignorar_paginas": [1, 2, 3, 4],
  "secoes": []
}
```

O documento é fatiado automaticamente em pedaços de cerca de 120 palavras, **sem cruzar página**,
para a citação de página sair exata.

- `ignorar_paginas`: capa, sumário, ficha técnica e referências. Tire tudo o que não é conduta.
- `padrao`: metadados de todas as páginas desse documento (ver tabela abaixo).

### 2. Marcar seções do documento (médio, melhora a precisão)

Um manual grande fala de muita coisa. Use `secoes` para dizer do que tratam certas páginas:

```json
"secoes": [
  { "paginas": "30-34", "subtipo": "traumatico", "condicao": "cabeca" },
  { "paginas": "40-42, 45", "subtipo": "traumatico", "condicao": "membro", "tipo": "primeiros_cuidados" }
]
```

### 3. Trechos curados à mão (lento, qualidade máxima)

É o que mais importa para a demo. Crie um arquivo por tema em `rag/curados/`
(ex.: `dengue.json`, `trauma_cabeca.json`), para ninguém mexer no mesmo arquivo.
Arquivos que começam com `_` são ignorados (o `_modelo.json` é só o exemplo).

```json
[
  {
    "id": "dengue_nao_fazer_01",
    "texto": "texto copiado do PDF, IGUAL ao original",
    "fonte": "dengue_manejo",
    "pagina": 12,
    "tipo": "nao_fazer",
    "subtipo": "espontaneo",
    "condicao": "dengue",
    "palavras_chave": ["mancha roxa", "roxo", "remedio", "aas", "melhoral"]
  }
]
```

Regras dos trechos curados:

- **Uma conduta por trecho.** Curto: 1 a 3 frases.
- **Copie igual ao PDF.** O indexador confere se o texto está na página citada. Pode cortar
  pedaços com `...`, e cada pedaço é conferido.
- **`pagina` é a página do leitor de PDF** (Pré-Visualização/Chrome), contando a capa como 1,
  e não o número impresso no rodapé.
- **`palavras_chave` é o vocabulário do ACS.** O protocolo diz "equimose", o ACS diz "roxo".
  O protocolo diz "ácido acetilsalicílico", o ACS diz "melhoral". Esse campo liga os dois
  na busca e pesa muito na nota.
- `id`: `<tema>_<tipo>_<nn>`, único no projeto todo.

## Valores dos metadados

| Campo      | Valores                                                                 |
|------------|-------------------------------------------------------------------------|
| `subtipo`  | `traumatico` (teve pancada) · `espontaneo` (sem pancada) · `geral` (os dois) |
| `condicao` | `cabeca` · `tronco` · `membro` · `dengue` · `cobra` · `anticoagulante` · ou omitir (vale para todo o subtipo) |
| `cores`    | opcional. Lista de cores em que o trecho pode aparecer, ex.: `["verde", "amarelo"]` para "pode ficar em casa". Omitir = qualquer cor |
| `tipo`     | `primeiros_cuidados` · `nao_fazer` · `sinais_de_alerta` · `quando_voltar` · `informacao` |

Em caso **vermelho ou laranja**, trechos do tipo `quando_voltar` nunca entram (não se orienta "ficar em casa" num caso grave).

O filtro vem **do caso**, não da pergunta: num caso de pancada na cabeça, só entram trechos
`traumatico`/`geral` com condição `cabeca` ou sem condição.

## Indexar e testar

```bash
.venv/bin/python -m rag.indexar
```

O indexador mostra:
- `AVISO ... texto NÃO encontrado na página X`: o trecho entra no índice marcado como
  `conferido=false`. Corrija o texto ou a página.
- `ERRO ...`: o trecho **ficou fora** (campo faltando, id repetido, fonte que não existe).
- `nenhuma página com texto`: o PDF é escaneado e precisa de OCR.

Depois, teste a busca como o agente faria:

```bash
.venv/bin/python -m rag.buscar "mancha roxa febre gengiva sangrando melhoral" --subtipo espontaneo --condicao dengue
.venv/bin/python -m rag.buscar "caiu bateu a cabeça vomitou" --subtipo traumatico --condicao cabeca
.venv/bin/python -m rag.buscar "picada de cobra" --so-curados
```

Se o trecho certo não aparece entre os 3 primeiros: reforce as `palavras_chave`, marque a
`secao` certa ou crie um trecho curado.

**Nota mínima (`--limiar`, padrão 0.5):** abaixo dela, o trecho é descartado e o app diz
"sem protocolo para essa situação, contate a unidade". Depois de colocar os PDFs reais, rode
as buscas acima com `--limiar -99` para ver as notas e ajuste o valor (variável `RAG_LIMIAR`).

## Arquivos

```
rag/
  docs/          PDFs e textos originais (entrada)
  fontes.json    cadastro das fontes e metadados por página
  curados/       trechos curados, um arquivo por tema
  indice/        GERADO pelo indexar (não versionar)
  extrair.py     documento -> texto por página
  indexar.py     páginas + curados -> indice/trechos.jsonl (com validação)
  buscar.py      BM25 + filtro + nota mínima (e o CLI de teste)
  texto.py       normalização (sem acento, sem stopwords, radical)
```
