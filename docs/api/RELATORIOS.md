# API de Relatórios

`GET /api/relatorios/dashboard/` exige JWT e aceita os filtros opcionais
`propriedade` e `safra`.

A resposta contém `estrutura`, `financeiro`, `estoque`, `operacoes`, `maquinas`
e `fluxo_mensal`, além do instante de geração e dos filtros aplicados.
Indicadores são gerenciais e refletem os registros persistidos no momento da
consulta.

## Relatórios operacionais

`GET /api/relatorios/operacionais/` exige JWT e é estritamente somente leitura.
Aceita `cad_pro`, `propriedade`, `cultura`, `safra`,
`classificacao_codigo`, `armazem`, `data_inicio`, `data_fim`, `pagina` e
`por_pagina`. `secao` seleciona `saldos`, `producao`, `reservas`, `vendas`,
`entregas`, `movimentacoes` ou `rastreabilidade`.

A resposta contém totais gerais, subtotais por CAD/PRO e por propriedade e a
seção paginada. Saldos são lidos exclusivamente de `PosicaoSaldoGraos` pelo
selector oficial de grãos. Cada posição é contada uma única vez e preserva a
chave CAD/PRO + cultura + safra + classificação + armazenagem; vínculos entre
CAD/PRO e propriedades não participam da agregação. Em todos os níveis,
`saldo_disponivel_kg = saldo_fisico_kg - saldo_comprometido_kg`.

Produção e histórico vêm do ledger imutável. Quando a produção nasceu de uma
carga colhida, a rastreabilidade expõe carga, grupo e placa. Reservas e vendas
usam seus querysets oficiais; entregas permanecem vinculadas à venda,
movimentação e posição autoritativa. O lote de vendas continua sendo apenas o
adaptador operacional e não representa alocação física.

`GET /api/relatorios/operacionais/opcoes/` devolve o catálogo atual de filtros.
Qualquer tentativa de `POST`, `PUT`, `PATCH` ou `DELETE` nesses endpoints
retorna HTTP 405. Não há exportação nesta entrega porque o projeto não possui
um mecanismo gratuito já estabelecido para esse relatório.
