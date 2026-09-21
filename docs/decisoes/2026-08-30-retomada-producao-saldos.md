# Retomada de Produção e Saldos — 30/08/2026

Continuidade posterior no mesmo dia: veja
[Integridade e concorrência de cargas rateadas](2026-08-30-integridade-rateios.md)
para as correções adicionais e os resultados mais recentes da suíte completa.

## Objetivo e ponto de continuidade

Continuação da tarefa de 29/08, identificada no histórico como
“Refazer histórico desde 26 de agosto”. O trabalho está no worktree
`D:/PROJETOS/AGRO-AI-PRO/.worktrees/runtime-origin-main`, branch
`codex/remover-grupos-colheita`, base `8a0c862`.

A pasta principal permanece em `feature/importacoes-confirmacao-v1`.
Os arquivos não rastreados, backups e demais worktrees preexistentes foram
preservados. Não houve troca de branch, commit, push ou merge nesta retomada.

A entrega herdada contém cargas diretas, armazenagem independente, rateio por
propriedade/CAD/PRO e propriedade produtora explícita em lotes e posições.
As migrations 0010, 0011 e 0012 já estavam presentes e foram confirmadas como
aplicadas no PostgreSQL operacional. Nenhuma migration foi criada ou editada
nesta retomada. O índice de Sprints não mudou: esta é uma correção da entrega
em andamento, não uma nova Sprint.

## Critérios de aceite verificados

- Preservar o trabalho de 29/08 e não misturar alterações da pasta principal.
- Filtrar lotes pelo campo de propriedade produtora, sem incluir lotes de outra
  propriedade apenas porque compartilham o CAD/PRO ou o armazém.
- Bloquear o crédito quando o lote selecionado deixa de pertencer ao filtro atual.
- Manter testes, build e migrations consistentes.
- Restaurar o ambiente local na porta 5174 sem excluir banco, volumes ou backups.

## Correção desta retomada

O painel já filtrava posições pela propriedade produtora. Entretanto, o seletor
de lotes do formulário de crédito ainda usava os vínculos do CAD/PRO. Quando
duas propriedades compartilhassem o mesmo CAD/PRO, o formulário poderia oferecer
um lote da propriedade errada.

O seletor agora compara diretamente `lote.propriedade_id`. O formulário também
verifica se o lote continua entre as opções válidas antes da submissão e
desabilita o botão caso contrário. A armazenagem permanece independente.
O teste de regressão cobre CAD/PRO compartilhado, armazém compartilhado,
armazenagens distintas, lote inativo, lote sem CAD/PRO e propriedade histórica
nula. Os tipos de lote e posição passaram a representar essa nulabilidade.

Arquivos alterados nesta retomada:

- `frontend/src/pages/ProducaoSaldos/ProducaoSaldosPage.tsx`;
- `frontend/src/api/producaoSaldos.ts`;
- `frontend/scripts/test-components.mjs`;
- `docs/api/GRAOS.md`;
- este relatório (novo).

As demais alterações locais de backend, frontend e documentação são anteriores
a esta retomada e foram mantidas. Nenhuma dependência foi adicionada.

## Validação automatizada

Comandos de backend SQLite, executados na pasta `backend`:

```powershell
$env:DJANGO_SETTINGS_MODULE='config.settings.test'
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test --noinput
```

Resultado: check sem problemas, nenhuma alteração de migration detectada;
268 testes encontrados, 239 executados com sucesso e 29 ignorados pelas
condições da suíte (incluindo testes que exigem PostgreSQL).

Comandos PostgreSQL, executados na raiz do worktree:

```powershell
docker compose -p agro-ai-pro exec -T -w /app/backend backend python manage.py check
docker compose -p agro-ai-pro exec -T -w /app/backend backend python manage.py makemigrations --check --dry-run
docker compose -p agro-ai-pro exec -T -w /app/backend backend python manage.py migrate --check
docker compose -p agro-ai-pro exec -T -w /app/backend backend python manage.py test --noinput --keepdb
docker compose -p agro-ai-pro exec -T -w /app/backend backend python manage.py showmigrations graos
```

Resultado: verificações aprovadas, 268 testes encontrados, 263 executados com
sucesso e 5 ignorados previstos; banco de testes separado preservado por
`--keepdb`. Todas as migrations de Grãos, até 0012, marcadas como aplicadas.

Comandos frontend, executados na pasta `frontend`:

```powershell
npm.cmd test
npm.cmd run build
git -c core.safecrlf=false diff --check
```

Resultado: 25 cenários de componentes/submissão/geometria/PWA e 13 de
autenticação aprovados; TypeScript e build aprovados; diff sem erros de espaço.
Não existe script `lint` no `package.json` desta entrega.

## Ambiente e validação visual

Docker Desktop e os quatro containers estavam desligados. Foram iniciados os
containers existentes, confirmando previamente o bind mount do backend para este
worktree. O frontend foi recompilado e atualizado com:

```powershell
docker compose -p agro-ai-pro build frontend
$env:FRONTEND_PORT='5174'
docker compose -p agro-ai-pro up -d --no-deps frontend
docker compose -p agro-ai-pro ps
```

Resultado final: backend, frontend, PostgreSQL e Redis saudáveis; frontend
`http://127.0.0.1:5174/` com HTTP 200 e healthcheck da API retornando `status: ok`.

No navegador, usando a sessão existente:

- Produção e Saldos abriu sem erros de console;
- selecionar uma propriedade restringiu o seletor de lotes e a tabela de saldos;
- selecionar um lote válido habilitou o botão de crédito;
- trocar a propriedade desabilitou o crédito do lote anterior;
- nenhum formulário de gravação foi submetido no banco operacional.

O cenário de duas propriedades com o mesmo CAD/PRO foi verificado pelo teste
automatizado; não foram criados dados operacionais para reproduzi-lo na tela.

## Limitações e próxima ação

- O build mantém aviso não bloqueante de bundle JavaScript acima de 500 kB.
- Registros históricos sem propriedade produtora continuam na consulta geral,
  sem atribuição automática baseada no armazém ou nos vínculos do CAD/PRO.
- Esta retomada não reatribuiu nem reconciliou dados históricos operacionais.
- Alterações anteriores e migrations 0010–0012 continuam sem commit; devem ser
  incluídas juntas na revisão e entrega para não separar código e esquema.
- Commit e push dependem de autorização expressa; merge depende da aprovação
  do Product Owner, conforme `AGENTS.md`.

Ponto de continuidade: entrega local validada e disponível para revisão do
Product Owner. Não iniciar uma nova Sprint nem limpar arquivos preexistentes
como parte implícita dessa revisão.
