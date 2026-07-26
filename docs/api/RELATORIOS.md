# API de Relatórios

`GET /api/relatorios/dashboard/` exige JWT e aceita os filtros opcionais
`propriedade` e `safra`.

A resposta contém `estrutura`, `financeiro`, `estoque`, `operacoes`, `maquinas`
e `fluxo_mensal`, além do instante de geração e dos filtros aplicados.
Indicadores são gerenciais e refletem os registros persistidos no momento da
consulta.
