# API de Relatórios

`GET /api/relatorios/dashboard/` exige JWT e aceita os filtros opcionais
`propriedade` e `safra`.

A resposta contém `estrutura`, `financeiro`, `estoque`, `operacoes`, `maquinas`
e `fluxo_mensal`, além do instante de geração e dos filtros aplicados.
Indicadores são gerenciais e refletem os registros persistidos no momento da
consulta.

## Relatórios operacionais

A interface usa o padrão numérico brasileiro em kg, alqueires paulistas, sacas e médias:
ponto somente para milhares e vírgula para decimais, com três casas (por exemplo,
`41.265,000 kg`, `28,926 alq.`, `687,750 sc` e `23,777 sc/alq.`). Contagens não exibem
casas decimais. CAD/PRO, safra, contratos e identificadores permanecem como texto.
Valores ausentes ou inválidos são indicados por travessão, sem inventar saldo zero.
O contrato JSON continua usando decimais canônicos com ponto; a formatação é
aplicada apenas na apresentação, sem recalcular ou gravar estoque.

`GET /api/relatorios/operacionais/` exige JWT e é estritamente somente leitura.
Aceita `cad_pro`, `propriedade`, `cultura`, `safra`,
`classificacao_codigo`, `armazem`, `data_inicio`, `data_fim`, `pagina` e
`por_pagina`. `secao` seleciona `saldos`, `producao`,
`producao_propriedade`, `reservas`, `vendas`, `entregas`, `movimentacoes` ou
`rastreabilidade`.

A resposta contém totais gerais, subtotais por CAD/PRO e por propriedade e a
seção paginada. Saldos são lidos exclusivamente de `PosicaoSaldoGraos` pelo
selector oficial de grãos. Cada posição é contada uma única vez e preserva a
chave propriedade produtora + CAD/PRO + cultura + safra + classificação + armazenagem; vínculos entre
CAD/PRO e propriedades não participam da agregação. Em todos os níveis,
`saldo_disponivel_kg = saldo_fisico_kg - saldo_comprometido_kg`.

Produção e histórico vêm do ledger imutável. Quando a produção nasceu de uma
carga colhida, a rastreabilidade expõe carga, status, propriedade, CAD/PRO,
cultura, safra e placa. Reservas e vendas usam seus querysets oficiais; entregas
permanecem vinculadas à venda, movimentação e posição autoritativa. O lote de
vendas continua sendo apenas o adaptador operacional e não representa alocação
física.

As seções produtivas de cargas e motoristas consideram apenas cargas `ativa`.
Uma carga `cancelada` ou `substituida` deixa de compor os totais, mas permanece
auditável com seu crédito original, estorno, snapshot e eventual substituta no
ledger.

O período respeita a data própria de cada seção. Em particular, entregas são
selecionadas por `data_entrega`, mesmo quando a venda foi contratada antes do
período consultado; vendas continuam sendo selecionadas por `data_contrato`.

A seção de rastreabilidade apresenta origem, referência, efeito no ledger,
snapshots de saldo anterior e posterior, posição oficial, lote operacional e,
quando houver, identificador e status da carga colhida, propriedade, CAD/PRO,
cultura, safra e placa. Isso preserva a trilha mesmo após estorno ou
substituição.

A seção `producao_propriedade` agrupa a produção por propriedade produtora,
CAD/PRO, cultura e safra. Ela informa área em hectares e em alqueires
paulistas, peso em kg, sacas de 60 kg, quantidade destinada a semente,
quantidade armazenada fora da propriedade produtora e média de sacas por
alqueire. A conversão usa exatamente `1 alqueire paulista = 2,42 hectares`.
Os totais abrangem todos os resultados filtrados, não apenas a página atual, e
a média total é calculada por `total de sacas / total de alqueires`, sem média
simples das médias das linhas.

Para cargas rateadas, cada crédito e seu estorno identificam a carga original
e a propriedade/CAD/PRO da respectiva parcela persistida, inclusive as parcelas
secundárias. Placa e estado vêm da carga, enquanto quantidade, efeitos e
snapshots continuam vindo do movimento. Uma retificação distingue a carga
substituída da nova carga; não atribui todos os movimentos à versão mais recente.
O carregamento dessas relações não acrescenta consultas por linha do relatório.

Os filtros por propriedade/CAD/PRO e os totais continuam baseados na posição
oficial. Não há multiplicação do peso total da carga pelo número de parcelas.
Cargas históricas sem rateio persistido mantêm seu vínculo direto com o crédito
original e o estorno, sem reconstrução ou gravação de movimentos.

`GET /api/relatorios/operacionais/opcoes/` devolve o catálogo atual de filtros.
Qualquer tentativa de `POST`, `PUT`, `PATCH` ou `DELETE` nesses endpoints
retorna HTTP 405. Na interface, a impressão da produção por propriedade permite
selecionar de forma reversível as colunas visíveis; a prévia e a impressão usam
a mesma seleção e apresentam os somatórios correspondentes. Não há geração de
arquivo de exportação nesta entrega porque o projeto não possui um mecanismo
gratuito já estabelecido para esse relatório.
