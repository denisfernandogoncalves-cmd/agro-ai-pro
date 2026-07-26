# API de Estoque

Todos os endpoints exigem autenticação JWT e usam o prefixo `/api/estoque/`.

## Cadastros

- `GET|POST /produtos/`
- `GET|PUT|PATCH|DELETE /produtos/{id}/`
- `GET|POST /locais/`
- `GET|PUT|PATCH|DELETE /locais/{id}/`
- `GET|POST /lotes/`
- `GET|PUT|PATCH|DELETE /lotes/{id}/`

Produtos aceitam as categorias `insumo`, `herbicida`, `fungicida`,
`fertilizante`, `semente` e `outro`. As unidades aceitas são `kg`, `l`, `un`,
`sc` e `t`.

Um lote pertence a um produto e a um local, possui código e pode informar data
de validade. Cadastros vinculados a lotes ou movimentos não podem ser
excluídos; a API responde HTTP 409.

## Movimentações

- `GET|POST /movimentacoes/`
- `GET /movimentacoes/{id}/`

Campos principais:

- `tipo`: `entrada` ou `saida`;
- `lote` e `quantidade`: obrigatórios;
- `custo_unitario`: obrigatório para entrada;
- `data_movimento`;
- `documento_fiscal`: opcional;
- `propriedade`, `safra` e `observacoes`: opcionais.

A API rejeita saídas superiores ao saldo do lote. Movimentações não aceitam
edição nem exclusão e retornam o usuário e a data responsáveis pelo registro.

Filtros disponíveis: `tipo`, `lote`, `produto`, `local`, `propriedade`, `safra`
e busca por produto, lote, documento ou observação. A ordenação aceita data,
quantidade, custo e tipo.

## Posição e alertas

- `GET /lotes/posicao/`
- `GET /lotes/resumo/`

A posição retorna saldo por lote, unidade, localização, validade e indicadores
de vencimento e estoque mínimo. O resumo contabiliza produtos ativos, lotes com
saldo, lotes vencidos, lotes próximos do vencimento e itens abaixo do mínimo.
