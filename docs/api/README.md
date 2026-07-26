# API do AGRO-AI-PRO

## Autenticação

Crie um usuário administrativo com `python manage.py createsuperuser` e obtenha
um token:

```http
POST /api/auth/token/
Content-Type: application/json

{"username": "usuario", "password": "senha"}
```

Envie o access token nas chamadas protegidas:

```http
Authorization: Bearer <access_token>
```

O token pode ser renovado em `POST /api/auth/token/refresh/`.

## Propriedades

O endpoint `/api/propriedades/` oferece CRUD, busca textual e ordenação. Campos:

- `nome`, `municipio` e `area_hectares`: obrigatórios;
- `proprietario`, `uf` e `observacoes`: opcionais;
- `latitude` e `longitude`: opcionais, mas devem ser enviados em conjunto;
- `arquivo_kml`: polígono `.kml` opcional, com limite de 5 MB.

Quando um KML é enviado, o backend valida o XML e o polígono e substitui as
coordenadas pelo centroide calculado. A resposta também inclui GeoJSON, área
geodésica aproximada e a diferença para a área declarada. Uma propriedade
vinculada a talhões não pode ser excluída; nesse caso, a API responde HTTP 409.

Consulte os exemplos e critérios completos em
[`docs/sprints/SPRINT-01.md`](../sprints/SPRINT-01.md).

## Talhões

A documentação dos endpoints, histórico agronômico, filtros, paginação,
validações de área, processamento KML e limitações geoespaciais está em
[Talhões](TALHOES.md).

## Clima

O módulo oferece previsão de sete dias por propriedade, histórico local,
temperatura, chuva, umidade, vento e alertas agrícolas. Consulte os endpoints e
limites em [Clima](CLIMA.md).

## Mercado

O módulo de Mercado mantém o histórico mensal de soja, milho, trigo e Brent,
resume variações, acompanha cinco regiões do Corn Belt e permite cadastrar
notícias com fonte HTTPS. Consulte [Mercado](MERCADO.md).

## Financeiro

O módulo Financeiro oferece cadastros auxiliares, contas a pagar e receber,
liquidação, filtros e resumo de fluxo de caixa. Consulte
[Financeiro](FINANCEIRO.md).
