# Impressão de Produção e saldos no padrão de Vendas — 02/09/2026

## Solicitação

O Product Owner solicitou que o layout de impressão da aba **Produção e
saldos** fique semelhante ao layout utilizado em **Vendas**.

## Resultado

A impressão passa a exibir somente uma planilha dedicada em A4 retrato, com o
mesmo padrão visual de Vendas: título centralizado, cabeçalho verde, contexto
dos filtros, total destacado, bordas e tipografia de planilha.

A tabela apresenta propriedade, CAD/PRO, proprietário, cultura, safra,
classificação, armazenagem e os saldos físico, comprometido e disponível. O
rodapé soma todas as posições dos filtros aplicados. Formulários, cartões e
rastreabilidade continuam disponíveis na tela, mas não são impressos.

Não houve alteração em APIs, models, migrations ou dados existentes.

## Segurança

Antes da alteração foi criado e validado o backup privado
`backups/antes-impressao-producao-saldos-2026-09-02-163410-520822`, com código,
alterações locais, arquivos não rastreados, banco PostgreSQL, uploads, catálogo
e hashes SHA-256.
