# API de Mercado

Todas as rotas exigem JWT no cabeçalho `Authorization: Bearer <token>`.

## Cotações

- `GET /api/mercado/cotacoes/`
- `GET /api/mercado/cotacoes/resumo/`
- `POST /api/mercado/cotacoes/atualizar/`

Filtros aceitos na listagem:

- `produto`: `soja`, `milho`, `trigo` ou `brent`;
- `data_inicio` e `data_fim`: datas ISO;
- `ordering`: `data`, `valor` ou `produto`, com `-` para ordem decrescente.

O resumo inclui o último valor, a variação percentual contra o período anterior,
a tendência descritiva e um aviso de uso informativo.

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

Quando FRED ou Open-Meteo não responde de forma válida, a atualização retorna
HTTP 503 com mensagem tratada. Registros já persistidos permanecem disponíveis.
