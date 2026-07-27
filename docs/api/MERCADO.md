# API de Mercado

Todas as rotas exigem JWT no cabeçalho `Authorization: Bearer <token>`.

## Mercado Enterprise

### Painel integrado

```http
GET /api/mercado/cotacoes-enterprise/painel/?propriedade=1
```

Retorna os sete ativos, estado de atualização, Corn Belt, fatores de alta e baixa,
tendência de curto prazo e recomendação operacional. Quando `propriedade` é informada,
o contexto de estoque, lotes conjuntos e contratos respeita a autorização da PR #16.

### Série

```http
GET /api/mercado/cotacoes-enterprise/serie/?ativo=soja_cbot&janela=30d
```

Ativos:

- `soja_cbot`;
- `milho_cbot`;
- `trigo_cbot`;
- `farelo_soja`;
- `oleo_soja`;
- `brent`;
- `dolar`.

Janelas:

- `intraday`: snapshots persistidos nas últimas 24 horas;
- `5d`: série diária recente;
- `30d`: até 31 pontos diários.

### Atualização manual

```http
POST /api/mercado/cotacoes-enterprise/atualizar/
Content-Type: application/json

{"ativo": "soja_cbot"}
```

O corpo vazio solicita atualização de todos os ativos. A ação usa cache, lock e o mesmo
serviço do worker automático. Falha de uma fonte preserva o último valor válido.

### Configuração

```http
GET   /api/mercado/configuracoes-enterprise/
PATCH /api/mercado/configuracoes-enterprise/{id}/
```

Somente usuário administrativo pode alterar `habilitado` ou
`frequencia_minutos`. Criação e exclusão pela API retornam HTTP 405.

### Histórico de atualizações

```http
GET /api/mercado/atualizacoes-enterprise/?ativo=soja_cbot&ordering=-iniciada_em
```

Cada tentativa registra estado, fonte, chamadas realizadas, cache, pontos persistidos e
mensagem sanitizada. Tokens ou URLs com credenciais não são armazenados.

## Cotações legadas

- `GET /api/mercado/cotacoes/`
- `GET /api/mercado/cotacoes/resumo/`
- `POST /api/mercado/cotacoes/atualizar/`

Essas rotas permanecem para compatibilidade com séries mensais já cadastradas.

Filtros aceitos na listagem:

- `produto`: `soja`, `milho`, `trigo` ou `brent`;
- `data_inicio` e `data_fim`: datas ISO;
- `ordering`: `data`, `valor` ou `produto`, com `-` para ordem decrescente.

## Clima do Corn Belt

- `GET /api/mercado/corn-belt/`
- `POST /api/mercado/corn-belt/atualizar/`

A listagem aceita `regiao` e `ordering`. Regiões disponíveis:

- `iowa`;
- `illinois`;
- `indiana`;
- `nebraska`;
- `minnesota`.

## Notícias

- `GET|POST /api/mercado/noticias/`
- `GET|PUT|PATCH|DELETE /api/mercado/noticias/{id}/`

Campos: `titulo`, `resumo`, `fonte`, `url` HTTPS, `publicada_em` e `ativa`.
A listagem aceita `search`, `ativa` e `ordering`.

## Erros externos

Uma indisponibilidade retorna HTTP 503 na atualização manual, preserva registros
anteriores e agenda nova tentativa. O painel pode continuar respondendo com o último
dado válido marcado como desatualizado.

Documentação operacional: `docs/MERCADO-AUTOMATICO.md`.
