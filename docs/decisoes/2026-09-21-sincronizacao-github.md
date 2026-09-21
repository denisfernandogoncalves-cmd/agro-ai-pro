# Sincronização da versão atual com GitHub — 21/09/2026

## Objetivo e aceite

Preservar as alterações locais do aplicativo, enviar a versão atual para sua
branch no GitHub e preparar a atualização da main por pull request. Aceite:
backup íntegro, arquivos pendentes versionados, branch local igual à remota,
validações registradas e nenhuma alteração no banco do aplicativo.
Merge permanece sujeito à aprovação do Product Owner.

## Versão e escopo

- Branch: `codex/grupos-propriedades-colheita`.
- Origem: `.worktrees/runtime-origin-main`, cópia usada pelo aplicativo local.
- Base remota verificada: `bd6c274`, main do PR #25; ancestral desta branch.
- Preservadas as alterações preexistentes em compras/estoque, disponibilidade,
  financeiro/parcelamentos/boletos, importações, grupos de propriedades,
  descontos acumulados de cargas, relatórios, impressão e instalação Windows.
- Relação exata dos arquivos: diff do commit de sincronização e do pull request.
- A branch `feature/importacoes-confirmacao-v1` recebe separadamente o checkpoint
  antigo da pasta principal; não deve substituir esta versão atual.

## Validações executadas

Com Python do ambiente local e `DJANGO_SETTINGS_MODULE=config.settings.test`:

- `python manage.py check`: aprovado.
- `python manage.py makemigrations --check --dry-run`: sem alterações.
- `python manage.py test --noinput`: 418 testes, aprovado, 36 ignorados.
- `npm test`: 44 testes de componentes e 13 cenários de autenticação aprovados.
- `npm run build`: aprovado; aviso de bundle maior que 500 kB.
- Análise sintática dos Python pendentes e busca por padrões de tokens/chaves:
  nenhuma ocorrência identificada.

Limites: suíte executada com SQLite; cenários específicos de PostgreSQL não
foram reexecutados nesta sincronização. Não há script de lint no package.json.
Nenhuma migration foi aplicada ao banco real e nenhum serviço foi reiniciado.
Não houve implementação funcional nova durante a sincronização.

## Backup privado verificado

- `backups/sincronizacao-20260921-071624`: histórico Git e 13 worktrees,
  incluindo arquivos pendentes; ZIPs íntegros e hashes SHA-256 no manifesto.
- `backups/agro-ai-pro-2026-09-21-071614-809186`: código, uploads e banco PostgreSQL
  parado, cópia física somente leitura; 7.941 entradas verificadas e hashes.

Backups e credenciais não são enviados ao GitHub. Nenhuma restauração realizada.
