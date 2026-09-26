# API do agente (para o front)

```bash
.venv/bin/uvicorn app.main:app --port 8000                          # LLM simulado (não precisa do modelo)
LLM_PROVEDOR=ollama .venv/bin/uvicorn app.main:app --port 8000      # modelo local
```

- Base: `http://localhost:8000`. CORS liberado (o front pode rodar em outro servidor local).
- Se existir a pasta `web/`, ela é servida em `/web/` e `/` redireciona para lá.
- **Offline:** o front não pode usar CDN (fontes, bibliotecas). Tudo local.
- Cada chamada ao modelo leva ~3 s (a orientação ~4-9 s): mostre "pensando…" e desabilite o botão.

## Tela do ACS

| Método | Rota | Corpo | Resposta |
|---|---|---|---|
| GET | `/api/config` | | `{llm, comunidades[], sinal}` |
| POST | `/api/casos` | `{idade?, comunidade}` (texto livre; acento e maiúscula não importam) | `Caso` |
| POST | `/api/casos/{id}/mensagens` | `{texto}` | `Caso` |
| POST | `/api/casos/{id}/foto` | `{imagem: "data:image/jpeg;base64,..."}` (até 5 MB) | `Caso` |
| POST | `/api/casos/{id}/confirmar` | | `{caso, ficha}` |
| GET | `/api/casos/{id}` | | `Caso` |

**Fluxo:** abrir caso → mostrar `caso.ultima_pergunta` → enviar resposta → repetir enquanto
`caso.status == "coletando"` → quando `"finalizado"`, mostrar o resultado → botão **Confirmar**.

### Campos do `Caso` que a tela usa
```jsonc
{
  "id": "7c4a6fbb",
  "status": "coletando | finalizado | confirmado",
  "ultima_pergunta": "Teve febre nos últimos dias?",
  "historico": [{"autor": "agente | acs", "texto": "..."}],     // o chat
  "passos": [{"n": 1, "ferramenta": "avaliar_risco", "quem": "llm | codigo | rag | guardrail | pessoa",
              "entrada": {}, "saida": {}, "ms": 0}],            // painel de raciocínio
  "classificacao": {"cor": "vermelho | laranja | amarelo | verde", "motivos": ["..."], "recursos": ["..."]},
  "assumidos": ["sinais_cabeca"],                               // pior cenário assumido
  "destino": {"em_casa": false, "nome": "Unidade Mista de Vila Nova", "tempo_barco_min": 120,
              "explicacao": "Precisa de ...: X, 2h de barco. A mais próxima (...) não tem ..."},
  "orientacao": {
    "status": "ok | so_trechos | sem_protocolo",
    "fala": "texto com [ids] citados",                          // só quando status = ok
    "trechos": [{"id": "...", "texto": "...", "fonte_titulo": "...", "pagina": 12,
                 "conferido": true, "nota": 3.2}],              // mostrar embaixo, com fonte e página
    "problemas_verificador": ["..."]                            // quando so_trechos
  },
  "foto": "/fotos/7c4a6fbb.jpg",
  "ficha_id": 1
}
```
- `destino == null` → comunidade fora da tabela de distâncias: mostrar "contate a unidade de referência".
- `sem_protocolo` → mostrar "Sem protocolo para essa situação, contate a unidade".
- `so_trechos` → não há fala; mostrar só os trechos originais.
- Cores do painel de raciocínio por `quem`: llm roxo, codigo azul, rag verde, guardrail âmbar, pessoa cinza.

## Sinal (simulado) e fila

| Método | Rota | Corpo | Resposta |
|---|---|---|---|
| GET | `/api/sinal` | | `{ligado, na_fila}` |
| POST | `/api/sinal` | `{ligado: true/false}` | `{ligado, enviadas_agora, na_fila}` |

Sem sinal, a ficha confirmada fica `na_fila`. Ao ligar, tudo vai para `enviada`.

## Painel da unidade

`GET /api/fichas?status=enviada` (opcional `&unidade=unidade_mista_vila_nova`), consultado a cada 2 s.
Já vem ordenado: vermelho primeiro, depois o mais recente.

```jsonc
[{"id": 1, "cor": "vermelho", "status": "enviada", "criada_em": "...", "enviada_em": "...",
  "chegada_prevista": "2026-09-26T14:11", "idade": 34, "comunidade": "São João do Lago",
  "motivos": ["..."], "destino_nome": "Unidade Mista de Vila Nova", "em_casa": false,
  "destino_explicacao": "...", "foto": "/fotos/7c4a6fbb.png", "campos": {}}]
```

## Demo

`POST /api/reiniciar` zera casos, fichas, fotos e sinal.
