# Transferências de terceiros — seis melhorias autorizadas

## Entrega e critérios

- Botão sempre presente por recebimento, bloqueado com motivo em cancelamento,
  saldo zero ou falta de permissão de cadastro em cargas e transferências.
- Status destacado: ativo, cancelado ou saldo esgotado.
- Filtro inicial de ativos e consultas de cancelados, esgotados e todos no
  servidor antes da paginação. Ativo significa não cancelado, inclusive esgotado.
- Prévia: terceiro, propriedade/CAD/PRO, quantidade, saldo restante da origem
  e disponível da destinatária por produto/safra/armazém.
- Comprovante PDF e Excel (.xlsx) com destino registrado, cadastros atuais
  identificados, motivo, responsável e situação. Exige impressão nos dois módulos.
- Recebimentos de terceiros separados em Produção e saldos por posição filtrada.
  Quantidades recebidas acumuladas, descontados os estornos; não são o saldo
  remanescente exclusivo de uma origem após mistura, vendas ou retiradas.

## Validação

11 testes PostgreSQL isolados aprovados (melhorias agendadas e romaneios de
cargas): filtros, saldos, estoque físico conservado, relatórios sem produção
adicional, PDF, conteúdo Excel, permissões e estorno. Frontend: componentes,
16 cenários de autenticação, seis de rascunhos, usabilidade, TypeScript e Vite
aprovados no build Docker. Sem migration ou dependência nova.
Aplicação local atualizada e saudável. Conferência autenticada confirmou filtro
inicial Ativos sem recebimentos e quatro Cancelados com status, botão visível
desabilitado e motivo explícito. Não houve movimentação de estoque no QA.
Migrations sem alterações pendentes e git diff --check aprovado.

Backup verificado: `backups/agro-ai-pro-2026-10-07-150845-129884`, código,
banco, uploads, hashes e restauração isolada. Alterações anteriores preservadas.

## Limites

A prévia é uma consulta; o servidor revalida saldo, versão, permissões e
concorrência ao salvar. Sem consulta de Produção e saldos, informa a falha de
consulta do destino; a autorização existente para transferir permanece.
O armazém físico não muda. Sem reclassificação histórica ou atribuição automática
de consumo a terceiros. Testes não criaram dados fictícios operacionais.
Sem commit, push, merge ou publicação em produção.
