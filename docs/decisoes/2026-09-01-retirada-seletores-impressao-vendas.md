# Retirada dos seletores de impressão de Vendas — 01/09/2026

## Solicitação

O Product Owner solicitou retirar da tela de Vendas os painéis **Informações da
impressão** e **Propriedades da impressão**.

## Resultado

Os dois painéis foram removidos. A impressão passa a incluir automaticamente as
nove colunas da planilha e todas as propriedades contidas no resultado dos
filtros de Vendas. As preferências antigas eventualmente gravadas no navegador
deixam de influenciar a tela e a impressão.

O rodapé continua somando peso e sacas das linhas impressas. Os filtros de
contrato/cliente, status, cultura, safra, classificação e histórico continuam
definindo o conjunto consultado e impresso.

## Segurança

Antes da alteração foi criado e validado o backup privado
`backups/antes-retirada-seletores-vendas-2026-09-01-214438-375717`, incluindo
código, alterações locais, banco PostgreSQL, uploads, catálogo e hashes SHA-256.
Não houve migration nem alteração de dados.
