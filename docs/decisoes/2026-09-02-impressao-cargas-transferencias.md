# Impressão de Cargas e Transferências no padrão de Vendas — 02/09/2026

## Solicitação

O Product Owner solicitou aplicar em **Cargas colhidas** e **Transferência de
saldo** o mesmo padrão de impressão já usado em Vendas e Produção e saldos.
Também definiu como regra geral usar orientação paisagem quando necessário para
maximizar a área útil da impressão.

## Resultado

As duas abas passam a imprimir somente planilhas dedicadas, com título,
cabeçalho verde, contexto, total destacado, bordas e rodapé de totalização.

- Cargas colhidas totaliza peso bruto, peso líquido e sacas das cargas filtradas.
- Transferência de saldo reúne débito e crédito em uma linha e totaliza a
  quantidade transferida.
- Formulários, filtros, botões e cartões operacionais permanecem na tela e são
  omitidos do papel.

As quatro planilhas largas — Vendas, Produção e saldos, Cargas colhidas e
Transferência de saldo — usam A4 paisagem com margens de 1 cm. Impressões menos
largas permanecem em A4 retrato.

Não houve alteração em APIs, models, migrations ou dados existentes.

## Segurança

Antes da alteração foi criado e validado o backup privado
`backups/antes-impressao-cargas-transferencias-2026-09-02-165220-774435`, com
código, alterações locais, arquivos não rastreados, banco PostgreSQL, uploads,
catálogo e hashes SHA-256.
