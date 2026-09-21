# Retirada do controle de estoque da tela Cargas colhidas — 02/09/2026

## Solicitação

O Product Owner solicitou retirar da tela **Cargas colhidas** o painel **Controle
de estoque por propriedade**, incluindo seletor, resumo de produção e tabela por
propriedade.

## Resultado

O painel e seus cálculos exclusivos foram removidos do frontend. O formulário
de registro e correção de cargas, o rateio entre propriedades, a busca, o
histórico e os cartões de cargas permanecem inalterados. Os relatórios de
produção e estoque continuam disponíveis na aba **Relatórios**.

Não houve mudança em API, models, migrations ou dados existentes.

## Segurança

Antes da alteração foi criado e validado o backup privado
`backups/antes-retirada-controle-cargas-2026-09-02-162616-125307`, contendo o
estado do Git, código rastreado, alterações locais, arquivos não rastreados,
banco PostgreSQL, uploads, catálogo e hashes SHA-256.
