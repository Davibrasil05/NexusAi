# triagem-acs

Agente de IA **offline** que ajuda o ACS (Agente Comunitário de Saúde) de comunidades ribeirinhas
a triar um **hematoma**: conversa, dá a cor de risco, escolhe a unidade pelo recurso e orienta
com trechos do protocolo do Ministério da Saúde. Hackathon Norte / AKCIT Camp 2026 (26/09/2026,
congelamento 15h). Documentos de origem: `~/Downloads/plano_acao_tecnico.pdf`, `escopo_mvp.pdf`.

**Modo de trabalho:** uma parte por vez, só o que for pedido. Não construir módulos não pedidos.

## Quem decide o quê (invariantes, não quebrar)
- **LLM** interpreta a fala do ACS em campos, reescreve a pergunta e escreve a orientação. Tudo validado.
- **Código** (`app/regras.py`) decide o que perguntar, a cor e os recursos. O LLM nunca decide nem baixa a cor.
- Sinal de alerta é checado **a cada turno** → vermelho na hora. `"nao_sei"` conta como SIM.
- Campo de alerta já SIM não volta para NÃO (`_piora` em `app/agente.py`).
- Rede de segurança: `palavras.alertas_no_texto` marca alerta do texto bruto que o LLM perdeu.
- JSON inválido → 1 nova tentativa → fallback do código. Erro de conexão/timeout → fallback direto.
- Conflito LLM × palavras em `pancada` → descarta e pergunta de novo.
- Caso vermelho/laranja: sem trechos `quando_voltar`; trechos com `cores` só aparecem nessas cores.
- Frase sem fonte é **removida** da orientação (`remover_frases_sem_fonte`); só cai para "só trechos" se não sobrar frase citada.
- Sinal de alerta NÃO mencionado: o LLM não pode responder "não"/"não sei" por ele (`sem_evidencia` em `_extrair`); "sim" é sempre aceito.
- Negação depois da palavra ("febre não", "vomitou não teve") é reconhecida; "febre não passa" continua SIM.
- **Sem trecho, sem orientação.** Verificador (`rag/verificar.py`) barra citação inválida e remédio/dose fora dos trechos → mostra só os trechos.
- O ACS dá a palavra final.

## Estrutura
```
app/config.py        variáveis de ambiente (LLM_PROVEDOR mock|ollama, LLM_MODELO, RAG_LIMIAR...)
app/modelos.py       schemas Pydantic (CamposCaso, Caso, Passo, Classificacao, Destino, Orientacao)
app/regras.py        sinais de alerta, cor, campos que faltam, perguntas padrão, pior cenário
app/palavras.py      extrator por palavras-chave (mock, fallback, rede de segurança); negação para na vírgula
app/prompts.py       prompts: extrair, perguntar, orientar (user msg = JSON com "tarefa")
app/agente.py        loop: atualizar_caso → rede → avaliar_risco → perguntar | encerrar (destino + orientação)
app/main.py          API FastAPI (rotas em API.md); casos em memória
app/fichas.py        gerar_ficha + fila SQLite + sinal
app/unidades.py      buscar_unidades: menor tempo de barco entre as que têm TODOS os recursos
app/orientador.py    consulta do RAG montada do CASO + escolha de 1 trecho por tipo
app/llm/             base.py (contrato), mock.py, ollama.py
rag/                 extrair.py, indexar.py, buscar.py (BM25), verificar.py, texto.py, fontes.json, curados/
rag/COMO_ALIMENTAR.md  guia para quem adiciona protocolos
front/src/           React: App.jsx (telas), componentes/, textos.js (rótulos ACS), api.js
web/                 BUILD do front (gerado por `npm run build`; versionado para a demo rodar sem Node)
dados/unidades.json  4 unidades / 3 comunidades FICTÍCIAS
scripts/testar_modelo.py  JSON válido, acerto de campos, segundos por resposta
scripts/conversar.py      agente no terminal (--llm ollama --passos --roteiro "a|b|c")
```

## Comandos
```bash
.venv/bin/python avaliacao/avaliar.py [--llm ollama]            # golden.json (24 casos): cor, destino, trechos
.venv/bin/python avaliacao/avaliar_extracao.py [--llm ollama]   # extracao.json (34 falas): entendimento campo a campo
LLM_PROVEDOR=ollama .venv/bin/uvicorn app.main:app --port 8000
.venv/bin/python scripts/conversar.py --llm ollama --passos
.venv/bin/python scripts/testar_modelo.py qwen3:8b
.venv/bin/python -m rag.indexar
.venv/bin/python -m rag.buscar "febre gengiva sangrando" --subtipo espontaneo --condicao dengue
```

## Front
- Mobile first, claro, roxo #820AD1. Fonte Inter embutida (@fontsource), ícones lucide-react: nada de CDN.
- Depois de mudar `front/src`, rodar `cd front && npm run build` (senão a API serve o build antigo).
- Dev com recarga: `cd front && npm run dev` (porta 5173, repassa /api para a 8000).
- Chrome recente: `scrollIntoView` devolve Promise → efeitos do React SEMPRE com chaves `useEffect(() => { ... })`.

## Modelo local
- `qwen3:8b` (Q4_K_M) no Ollama 0.34. Mac arm64, 24 GB.
- **Raciocínio desligado** com `reasoning_effort="none"` (25 s → 3 s). `extra_body={"think": False}` NÃO funciona.
- Placar: JSON 5/5, acerto 95%, ~3 s/chamada. Coleta ~2-3 s por turno; orientação ~4-9 s.
- Perguntas são as do código (`PERGUNTAS` em regras.py): `LLM_REESCREVE_PERGUNTA=0` é o padrão. Uma ideia por pergunta, para Sim/Não/Não sei terem um sentido só.

## Estado (atualizar ao avançar)
- [x] 1. Cliente Ollama + teste de modelo
- [x] 2. Loop de coleta no terminal com guardrails
- [x] 3. Destino por recurso
- [x] 4. Orientação: RAG → LLM → verificador (testado com índice de teste; **índice real vazio** até o amigo alimentar)
- [x] 5. API FastAPI + ficha (SQLite dados/fichas.db) + fila offline + sinal simulado. Contrato: `API.md`
- [x] 6. Front React + Tailwind 4 (Vite) em `front/`; build versionado em `web/` (a API serve em /web/, painel em /web/#/painel)
- [x] 7. Testes: golden.json 24 casos (5 do Carlos + 19) e extracao.json 34 falas
- [ ] 8. Ensaio offline + vídeo de backup (~13h)

## Compatibilidade
- Carlos usa **Python 3.9**. Todo .py tem `from __future__ import annotations` DEPOIS da docstring.
- Onde o tipo é avaliado em tempo de execução (rotas FastAPI, campos Pydantic) usar `Optional[...]`, nunca `X | None`.
- Testar no 3.9: `/usr/bin/python3` (3.9.6) num venv à parte.

## Pendências conhecidas
- Laranja/amarelo em `regras.py` são PROPOSTA; validar com a equipe.
- `RAG_LIMIAR=0.5` é chute: calibrar com os PDFs reais (`rag.buscar ... --limiar -99`).
- `fontes.json`: URLs vazias; o amigo preenche. Fonte de peçonhentos adicionada (não estava no plano).
- Campo antigo `crescendo_ou_sangrando` foi dividido: `crescendo` (perguntado) e `sangramento_nao_para` (alerta só se o ACS falar).
- Comunidade é digitada; `resolver_comunidade` casa com a tabela sem acento. Fora da tabela: sem destino, "contate a unidade de referência".
