# Retomada de 10/09 após 17h

Branch: `codex/grupos-propriedades-colheita`, checkout `runtime-origin-main`.
Alterações anteriores preservadas, sem commit, push ou merge nesta retomada.

## Entrega

Retomado o leitor financeiro implementado em 10/09 e adicionado o atalho
**Novo lote** ao seletor da movimentação de Estoque. O cadastro abre com foco
no produto; o lote salvo fica selecionado e os demais campos são preservados.
O cadastro continua independente do registro de entrada/saída.

Arquivos alterados nesta retomada: `frontend/src/pages/Estoque/EstoquePage.tsx`,
`docs/api/ESTOQUE.md` e este registro. A migration preexistente
`financeiro.0002_codigo_barras` é aplicada pelo comando de início do backend.

## Backup

`backups/agro-ai-pro-2026-09-11-071306-131404`: código incluindo mudanças locais,
uploads e cópia física do PostgreSQL parado (5760 entradas). ZIPs verificados
por CRC e arquivos registrados com SHA-256 no `manifesto.json`.
Nenhuma restauração executada.

## Validação

- `npm.cmd test`: 40 testes de componentes e 13 cenários de autenticação aprovados.
- `npm.cmd run build`: aprovado; aviso de bundle maior que 500 kB.
- `docker compose -p agro-ai-pro run --rm --no-deps -T -w /app/backend backend python manage.py test apps.financeiro apps.estoque --noinput`: 42 testes aprovados.
- O comando anterior encontrou `test_agro_ai_pro` existente e o recriou
  automaticamente. Essa exclusão não deveria ter sido realizada sem decisão
  explícita; nas próximas execuções usar nome exclusivo e `--keepdb`.
- `makemigrations --check --dry-run` no container: nenhuma mudança detectada.
- `git -c core.safecrlf=false diff --check`: aprovado.
- Build Docker do frontend aprovado; frontend atualizado na porta 5174.
- Backend, frontend, PostgreSQL e Redis saudáveis após início.

Não foi repetida a suíte geral: o histórico de 10/09 registra execução com
sucesso; nesta retomada foi validado o escopo Financeiro/Estoque. Não há script
de lint no package.json. Conferência visual interativa e leitor USB físico
permanecem pendentes; testes existentes de frontend não cobrem a interação
completa do novo atalho.
