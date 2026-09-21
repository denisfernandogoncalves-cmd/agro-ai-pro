# Retomada do projeto após a pausa de 30/08/2026

Checkout: `D:/PROJETOS/AGRO-AI-PRO/.worktrees/runtime-origin-main`.
Branch: `codex/remover-grupos-colheita`, HEAD inicial `8a0c862`.
O checkout principal está em `feature/importacoes-confirmacao-v1`; não foi
trocada sua branch nem sobrescrito seu trabalho. O escopo foi recuperado de
`backups/pausa-2026-08-30-195208-084699/RETOMADA.md`, preservando as quatro
solicitações registradas. O índice de Sprints permanece inalterado: as Sprints
1–12 já estavam concluídas; esta é uma entrega incremental.

## Segurança e backups

- Backup da pausa: os nove arquivos conferiram em tamanho e SHA-256 com o manifesto.
- `backups/retomada-2026-08-31-073242-309305/`: código atual, inclusive alterações
  não commitadas, uploads, estado/diff Git e cópia física do volume PostgreSQL 17
  parado. Volume montado somente para leitura; 2.159 arquivos lidos integralmente.
- `backups/retomada-2026-08-31-073842-964299/`: backup lógico custom antes da
  migration, código e uploads; `pg_restore --list` e leitura integral aprovados.
- `backups/retomada-2026-08-31-074410-267990/`: cópia final de banco, código e
  uploads antes da última atualização do frontend, com as mesmas verificações.
- ZIPs verificados por CRC; manifestos SHA-256 nas pastas privadas, ignoradas pelo Git.
- Nenhum backup anterior sobrescrito, nenhuma restauração ou limpeza realizada.

Os 59 registros dos apps propriedades, cadpro, graos e vendas mantiveram o mesmo
hash de conteúdo antes/depois da migration:
`c2e9725fa836b1986ceb6d2a4d996431862c6c0473c9f88f328fb45828761280`.
Não foram enviados lançamentos reais durante os testes da interface.

## Resultado e critérios de aceite

1. Vendas sem saldo: fluxo existente da pausa validado com estoque negativo,
   início sem entrada prévia, replay, compensação por entradas parciais,
   reconciliação, devoluções, edição, exclusão e cancelamento. Validação inválida
   reverte venda, reserva e contexto de estoque. Déficit não libera capacidade
   ocupada em outra posição. Reservas genéricas mantêm proteção de saldo.
2. Cartões por propriedade: teste com três propriedades e dois CAD/PROs,
   filtro por produtora, histórico sem propriedade e conservação dos totais.
   Navegador confirmou três cartões e contagens independentes (3 propriedades,
   2 CAD/PROs, 7 posições existentes no momento da conferência).
3. Transferências: teste de CAD/PRO igual/diferente entre propriedades, proteção
   de reserva e bloqueio da própria posição, inclusive com lotes distintos.
   Corrigida aquisição dos locks de ambos os CAD/PROs e lotes em ordem estável;
   teste PostgreSQL de transferências opostas aprovado.
4. Impressão: botão global, A4 retrato, margens superior/esquerda 3 cm e
   inferior/direita 2 cm. Imprime a consulta/página exibida; não busca páginas
   adicionais. Identifica módulo/seção, expande detalhes temporariamente e
   preserva classes de ocultação preexistentes ao restaurar a interface.
   **Validação visual da impressão ainda pendente:** o navegador integrado não
   apresentou prévia após o clique. Não foi validado PDF, papel, cancelamento do
   diálogo nativo ou paginação visual em todas as abas. Conferir em Chrome/Edge.

## Arquivos desta retomada

Além das alterações herdadas, foram modificados:

- `backend/apps/graos/services.py`: locks de transferências;
- `backend/apps/graos/test_transferencia_cadpro_interface.py`: novas regras;
- `frontend/scripts/test-components.mjs`: opções zero/negativas, novas origens
  e compatibilidade de transferências;
- `frontend/src/components/ImprimirA4.tsx`: contexto e restauração da impressão;
- `docs/api/GRAOS.md` e `docs/api/VENDAS.md`: contratos atualizados.

Criados `backend/apps/vendas/test_saldo_negativo.py`,
`backend/apps/graos/test_retomada_saldos.py` e este relatório.
Nenhum arquivo funcional foi removido. A migration 0013 já existia não rastreada
na pausa: foi preservada e aplicada, sem editar migrations antigas.

## Verificações

Comandos Docker executados neste checkout, projeto Compose `agro-ai-pro`:

- `docker compose -p agro-ai-pro run --rm --no-deps -T -w /app/backend backend python manage.py test --noinput`:
  **329 testes encontrados, 324 aprovados, 5 ignorados**, 152,588 segundos.
  Inclui concorrência real e ciclos de migrations em banco de teste.
- `npm.cmd test` no frontend: **40 cenários de componentes/submissão/geometria/PWA
  e 13 de autenticação aprovados**. Expectativas antigas que excluíam saldo zero
  e bloqueavam outra propriedade foram corrigidas conforme autorização da pausa.
- `npm.cmd run build`: aprovado, incluindo TypeScript; aviso preexistente de
  bundle maior que 500 kB. Não existe script separado de lint.
- `manage.py makemigrations --check --dry-run`: nenhuma alteração detectada.
- `manage.py migrate --plan`: somente `graos.0013_permitir_saldo_negativo_vendas`.
- `manage.py migrate --noinput`: 0013 aplicada com sucesso no ambiente local.
- `manage.py check` e `manage.py migrate --check`: aprovados após atualização.
- `docker compose -p agro-ai-pro build frontend`: aprovado; ambiente atualizado
  mantendo `FRONTEND_PORT=5174`. Backend, frontend, PostgreSQL e Redis saudáveis.
- `git -c core.safecrlf=false diff --check`: aprovado.

A primeira execução SQLite (140 testes) encontrou uma expectativa antiga de
transferência; o cenário foi corrigido e passou no PostgreSQL. Os testes novos
tiveram erros iniciais de fixture/argumento corrigidos antes da suíte completa.
Uma chamada de descoberta feita fora de `/app/backend` encontrou zero testes;
foi descartada como evidência e repetida corretamente com os 329 testes acima.

## Limitações e próximos passos

- Concluir a conferência visual A4 em navegador com diálogo de impressão.
- Retornar a migration 0013 sobre saldo negativo pode falhar pelas constraints
  antigas; não restaurar banco nem alterar saldos para contornar isso.
- Alterações anteriores de cargas, contratos e demais módulos permanecem no
  worktree, sem commit. Revisar o conjunto antes de autorizar sua entrega no Git.
- Sem commit, push, merge ou publicação em produção.
