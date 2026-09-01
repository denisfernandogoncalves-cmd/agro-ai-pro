# Identificação completa da origem em Nova venda

Pedido específico do Product Owner: substituir o seletor CAD/PRO no formulário
Nova venda por **Propriedade / CAD/PRO / Proprietário**.

Branch: `codex/remover-grupos-colheita`, checkout `.worktrees/runtime-origin-main`.
Alterações locais anteriores preservadas. Não há Sprint pendente no índice;
esta entrega é uma correção incremental do módulo Vendas.

## Implementação e aceite

- Seletor mostra propriedade, CAD/PRO e proprietário em cada opção.
- Propriedades distintas com o mesmo CAD/PRO não são agrupadas.
- Posição oficial oferece apenas os saldos da combinação selecionada.
- Trocar a origem limpa somente a posição, preservando os demais dados da venda.
- Envio valida novamente a posição contra a seleção. O backend continua
  responsável pela baixa atômica e pela proteção contra saldo insuficiente.
- Proprietário ausente tem indicação explícita. Saldos históricos sem propriedade
  não são atribuídos indevidamente a uma propriedade atual.

Arquivos: `frontend/src/pages/Vendas/VendasPage.tsx`, novo `origemVenda.ts`,
`frontend/src/api/vendas.ts`, `frontend/scripts/test-components.mjs` e
`docs/api/VENDAS.md`. Os proprietários são lidos pelo endpoint existente de
propriedades. Nenhum model, migration, regra de transferência ou dado foi alterado.

## Validação

- `npm test`: 40 cenários de componentes/submissão/geometria/PWA e 13 de
  autenticação aprovados. Novo cenário verifica propriedades com CAD/PRO
  compartilhado, saldos separados, várias posições da mesma origem, proprietário,
  ausência de saldo e origem histórica.
- `npm run build`: aprovado, incluindo TypeScript.
- Aviso existente de bundle acima de 500 kB permanece. Não existe script de
  lint separado no frontend.
- Suíte backend não repetida nesta alteração exclusivamente de interface e
  consumo de endpoint existente; a execução anterior teve 312 aprovados e
  5 ignorados, registrada no relatório de vendas/transferências.
- Build Docker e atualização apenas do frontend local em `127.0.0.1:5174`:
  aprovados. `manage.py check` sem problemas e `makemigrations --check --dry-run`
  sem alterações pendentes. `git -c core.safecrlf=false diff --check` aprovado.
- Navegador: opção LOTE 27 mostrou somente Trigo e 6.140,625 kg; trocar para
  SÍTIO SÃO SILVESTRE limpou a posição e mostrou somente seus dois saldos,
  mantendo o campo Destino preenchido. Nenhuma venda foi enviada.

## Backup e orientação permanente

Durante esta tarefa, o Product Owner determinou **sempre fazer backup**.
A atualização do frontend já estava em execução quando a orientação chegou;
foi criado imediatamente um backup do estado atual, antes das alterações
seguintes nas instruções permanentes. Não se trata de cópia anterior à edição
do seletor, que havia começado antes dessa nova orientação.

Cópia validada em `backups/seguranca-2026-08-30-193537-754525/` deste checkout:
banco PostgreSQL em formato custom, código atual com mudanças não commitadas,
arquivo de uploads (vazio, sem uploads neste ambiente), AGENTS.md anterior do
checkout principal, catálogo e manifesto com SHA-256. Banco validado por
`pg_restore --list` e leitura integral; ZIPs tiveram CRC verificado. Não foi
feita restauração completa de teste nem restauração sobre o banco ativo.

Backups anteriores preservados; pasta confirmada como ignorada pelo Git e
fora da área pública. A regra foi incluída em `AGENTS.md` neste checkout e no
checkout principal, para orientar as próximas tarefas.

Git: sem commit, push ou merge. Sem publicação em produção, exclusão ou
lançamentos de teste no banco operacional.
