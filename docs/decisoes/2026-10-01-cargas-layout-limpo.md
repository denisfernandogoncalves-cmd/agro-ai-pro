# Cargas colhidas: organização das informações

Pedido: tornar os cartões mais legíveis, preservando a apresentação compacta e a quebra de linhas conforme a tela.

Identificação e total ficam no cabeçalho. Pesos e desconto formam um bloco separado, com ações ao lado. Análises e rastreabilidade ficam em uma linha secundária que quebra automaticamente. Cargas compartilhadas possuem distribuição em um bloco próprio, com identificação e quantidades de cada propriedade. Em telas pequenas, as ações passam para uma linha própria. Nenhuma informação ou ação foi removida.

Arquivos: `frontend/src/pages/CargasColhidas/CargasColhidasPage.tsx` e `frontend/src/styles.css`, no checkout de execução `.worktrees/runtime-origin-main`.

Backup antes das alterações: `backups/sincronizacao-20261001-104935`, com código dos 13 worktrees, uploads, manifesto de hashes e banco PostgreSQL em `postgres.dump`. Dump validado com `pg_restore --list` (613 linhas); SHA-256 registrado em `manifesto-dump.json`.

Validação: `npm.cmd run build`, `npm.cmd test` e `git diff --check` aprovados. O build mantém o aviso de bundle acima de 500 kB. Sem alteração de banco ou migration. Verificação visual em navegador autenticado não executada nesta tarefa; a quebra depende de flex-wrap e colunas com largura mínima zero, sem rolagem horizontal forçada. Atualização do frontend local pelo Docker Compose. Sem commit, push ou merge.

## Ajuste de contraste

A pedido do usuário, nomes e totais usam verde escuro (#14543f), textos secundários cinza (#475569), e valores de análise cinza mais escuro (#1e293b). Cores restritas aos cartões de cargas; ações mantêm suas cores. Backup adicional: `backups/sincronizacao-20261001-105337`, com código, uploads e dump validado/hash registrado. Validação por build e testes do frontend, revisão do diff e entrega do CSS via HTTP local; sem avaliação visual no navegador autenticado.
