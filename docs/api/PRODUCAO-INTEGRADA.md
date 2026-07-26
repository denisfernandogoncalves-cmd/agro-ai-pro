# API — Gestão Integrada da Produção

Base: `/api/producao/`

Todos os endpoints exigem JWT. O backend filtra registros por propriedade e CAD/PRO antes de localizar objetos.

## Permissões

- superusuário: acesso completo;
- administrador: gestão completa da propriedade e de seus CAD/PRO;
- gestor: cadastros, contratos, relatórios, ajustes e importações nos CAD/PRO autorizados;
- operador: recebimentos, transferências e embarques nos CAD/PRO autorizados;
- somente leitura: listagens, Dashboard e relatórios.

IDs de propriedade ou CAD/PRO fora do escopo retornam HTTP 404. Ações incompatíveis com o papel retornam HTTP 403.

## Cadastros

| Recurso | Endpoint |
| --- | --- |
| Culturas | `/culturas/` |
| Safras | `/safras/` |
| CAD/PRO | `/cadpros/` |
| Acessos a CAD/PRO | `/acessos-cadpro/` |
| Motoristas | `/motoristas/` |
| Veículos | `/veiculos/` |
| Parceiros e compradores | `/api/financeiro/parceiros/` |
| Locais de armazenagem | `/api/estoque/locais/` |

## Recebimentos

`GET|POST /recebimentos/`

Campos principais:

- propriedade, CAD/PRO, talhão opcional, cultura e safra;
- motorista, veículo, placa informada e romaneio;
- peso bruto, tara e peso líquido em kg;
- umidade, impureza e defeitos;
- local de armazenagem;
- observações.

O cadastro inicial fica em rascunho. Para creditar o estoque:

```http
POST /api/producao/recebimentos/{id}/confirmar/
```

Para estornar um recebimento confirmado:

```http
POST /api/producao/recebimentos/{id}/estornar/
Content-Type: application/json

{"motivo": "Correção de pesagem"}
```

Registros confirmados não podem ser editados ou apagados.

## Estoque de grãos

### Saldos

`GET /saldos-graos/`

Filtros:

- `propriedade`
- `cadpro`
- `talhao`
- `cultura`
- `safra`
- `local`

### Movimentações

`GET|POST /movimentacoes-graos/`

Tipos manuais:

- `entrada`
- `saida`
- `transferencia`
- `ajuste_entrada`
- `ajuste_saida`
- `estorno`

Transferências exigem origem e destino diferentes. Saídas e ajustes negativos são rejeitados quando superam o saldo.

Estorno:

```http
POST /api/producao/movimentacoes-graos/{id}/estornar/
Content-Type: application/json

{"motivo": "Movimento lançado no local incorreto"}
```

## Contratos

`GET|POST|PATCH /contratos/`

Campos:

- propriedade, CAD/PRO, cultura e safra;
- comprador e número;
- data do contrato e data limite;
- quantidade em kg;
- preço por saca;
- tolerância percentual;
- status e observações.

O saldo contratual é calculado a partir dos embarques confirmados.

## Embarques

`GET|POST /embarques/`

Campos principais:

- propriedade, CAD/PRO, cultura, safra e armazenagem;
- comprador e contrato opcional;
- motorista, veículo, placa, destino e romaneio;
- número da nota do produtor e da empresa;
- quantidade em kg e preço por saca.

Confirmar:

```http
POST /api/producao/embarques/{id}/confirmar/
```

A confirmação:

1. bloqueia o saldo de origem;
2. valida o estoque e o saldo contratual;
3. cria a saída de grãos;
4. calcula sacas e valor;
5. cria uma conta a receber no Financeiro;
6. registra auditoria.

Estornar:

```http
POST /api/producao/embarques/{id}/estornar/
Content-Type: application/json

{"motivo": "Embarque cancelado pelo comprador"}
```

## Dashboard

`GET /dashboard-integrado/`

Filtros:

- `propriedade`
- `cadpro`
- `cultura`
- `safra`
- `data_inicio`
- `data_fim`

Retorna produção, sacas, cargas, qualidade média, estoque, embarques, receita, contratos e agrupamentos por propriedade, CAD/PRO e talhão. Quando há área do talhão, inclui produtividade em sacas por hectare.

## Relatórios

`GET /relatorios-integrados/`

Parâmetros:

- `tipo`: `recebimentos`, `embarques`, `estoque` ou `contratos`;
- `formato`: `json`, `csv`, `xlsx` ou `pdf`;
- propriedade, CAD/PRO, talhão, cultura, safra, local;
- comprador, contrato, motorista, placa e status;
- `data_inicio` e `data_fim`.

Exemplo:

```http
GET /api/producao/relatorios-integrados/?tipo=embarques&formato=xlsx&propriedade=1&comprador=4
```

## Importação de planilhas

`GET|POST /importacoes/`

Formatos: CSV, XLSX e XLSM, com limite de 10 MB.

O upload executa somente análise e pré-visualização. A resposta contém:

- colunas detectadas;
- mapeamento automático;
- prévia das linhas;
- inconsistências;
- total de linhas;
- status.

Um mapeamento manual pode ser validado novamente:

```http
POST /api/producao/importacoes/{id}/validar/
Content-Type: application/json

{"mapeamento": {"data": "Data", "peso_liquido_kg": "Peso Líquido"}}
```

A importação somente é aplicada após:

```http
POST /api/producao/importacoes/{id}/confirmar/
```

Se qualquer linha apresentar inconsistência durante a confirmação, a transação inteira é revertida.

## Auditoria

`GET /auditoria/`

Somente leitura. Registra usuário, ação, entidade, identificador, propriedade, metadados e data.
