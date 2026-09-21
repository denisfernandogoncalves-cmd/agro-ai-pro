# Continuidade de importações e grupos de colheita

## Objetivo e aceite

Continuar as duas entregas solicitadas pelo Product Owner, no checkout
`runtime-origin-main`, branch `codex/grupos-propriedades-colheita`.
Preservar as alterações existentes de grupos e cargas e adaptar o checkpoint
de confirmação `31eb6fe` ao domínio atual de grãos.

- Preview sem movimentação; confirmação explícita com permissão específica.
- Confirmação atômica, auditável e idempotente; duplicidade impedida no banco.
- Associação pela propriedade produtora, independente da armazenagem.
- Validar CAD/PRO ativo, vínculo, cultura, safra e classificação.
- Preservar grupos, preenchimento das cargas e rateio por área.
- Executar testes de importações, grupos e cargas, suíte geral, migrations,
  testes do frontend e build; registrar limitações.

## Preservação

Backup anterior às alterações em
`backups/retomada-2026-09-07-130148-639567`: código com alterações locais,
uploads e cópia física do PostgreSQL parado. ZIPs verificados por CRC,
leitura integral das 3584 entradas do banco e SHA-256 no manifesto.
Nenhuma restauração executada.

## Compatibilidade

A versão antiga identificava a origem pela propriedade do armazém. A versão
atual guarda `LoteGraos.propriedade`; utilizar esse campo evita creditar
produção à propriedade da armazenagem. Lotes históricos sem propriedade
produtora explícita não são associados automaticamente.

O endpoint preserva o adaptador oficial `registrar_movimentacao`, que encaminha
entradas para crédito de produção e saídas para ajuste do ledger atual.
Não cria cargas manuais nem altera suas regras de rateio.

A migration de confirmação original é preservada. Uma migration adicional
impede hashes repetidos entre linhas confirmadas, inclusive em concorrência.
Os bloqueios de confirmação usam apenas a tabela principal para compatibilidade
com joins opcionais no PostgreSQL.

## Validação final em 07/09/2026

Retomada final na mesma branch, preservando todos os arquivos locais. Novo
backup em `backups/retomada-2026-09-07-182034-952351`: código, uploads e
cópia física do PostgreSQL parado, com 4318 entradas lidas integralmente.
Os ZIPs passaram na verificação CRC; tamanhos e SHA-256 estão no
`manifesto.json`. Nenhuma restauração foi executada.

Comandos executados no checkout desta entrega:

- Backend, com `--settings=config.settings.test`: `python manage.py check`
  aprovado; `python manage.py makemigrations --check --dry-run` sem alterações;
  `python manage.py test` aprovado, 366 testes e 36 ignorados nessa configuração.
- PostgreSQL: `docker compose -p agro-ai-pro run --rm --no-deps
  -e POSTGRES_DB=continuacao_20260907_1820 backend sh -c 'cd /app/backend &&
  python manage.py test apps.importacoes apps.talhoes.tests.test_grupos_colheita
  apps.graos.test_consultas_rateios --keepdb --noinput'`: 48 testes aprovados.
  O banco de teste foi preservado. A falha simulada nos logs é parte do teste
  de rollback, que passou sem efeitos parciais.
- Frontend: `npm.cmd test` aprovado, incluindo componentes, importações,
  preenchimento dos grupos e 13 cenários de autenticação; `npm.cmd run build`
  aprovado. Não existe script de lint. Permanece aviso de bundle acima de 500 kB.
- `docker compose -p agro-ai-pro build frontend`: aprovado.
- Banco local: `migrate --check`, `makemigrations --check --dry-run` e `check`
  aprovados. `showmigrations importacoes talhoes` confirmou `importacoes.0002`,
  `importacoes.0003` e `talhoes.0008` já aplicadas; nenhuma migration nova
  foi necessária nesta retomada.
- Aplicativo iniciado com `docker compose -p agro-ai-pro up -d backend frontend`.
  Backend, frontend, PostgreSQL e Redis saudáveis. Frontend em
  `http://localhost:5173/` respondeu HTTP 200; `/api/health/` pelo frontend
  respondeu `status=ok`.
- Revisão final dos arquivos novos e do diff, com `git diff --check` aprovado.

A interface de importações permite prévia, revisão paginada e confirmação
explícita com permissão específica. Não edita associações ambíguas de staging;
elas bloqueiam a confirmação. Os grupos continuam opcionais e preservam o
rateio das cargas. Não foi realizada sessão visual autenticada de ponta a ponta;
a interface foi validada pelos testes automatizados e pelo build.

Nesta retomada, apenas este registro e o índice de Sprints foram atualizados;
o código existente foi revisado e validado. Não houve remoção de arquivos,
alteração de credenciais, commit, push, merge ou publicação em produção.
As alterações das duas entregas permanecem locais nesta branch.
