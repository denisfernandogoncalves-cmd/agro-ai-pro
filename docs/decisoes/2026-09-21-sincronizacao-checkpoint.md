# Sincronização GitHub — 21/09/2026

A pasta principal permanece na branch `feature/importacoes-confirmacao-v1`.
Este checkpoint preserva os 57 arquivos que estavam preparados para commit
na sincronização interrompida. Não representa a versão atual do aplicativo.

A versão atual está na cópia `.worktrees/runtime-origin-main`, branch
`codex/grupos-propriedades-colheita`, que deve ser avaliada para atualizar a main.

## Validação deste checkpoint

- `git diff --cached --check`: aprovado antes do commit.
- Análise sintática dos Python alterados e busca por padrões de tokens/chaves: sem ocorrências.
- `python manage.py check --settings=config.settings.test`: aprovado.
- `python manage.py makemigrations --check --dry-run --settings=config.settings.test`:
  bloqueado por dependência de `cadpro.0001_initial` não reconhecida nesta branch antiga.
- Suíte backend não executada: o grafo de migrations não carrega.
- `npm test`: 15 testes de componentes e 13 cenários de autenticação aprovados.
- `npm run build`: aprovado.

Não integrar este checkpoint à main como substituto da versão atual.
Nenhum código funcional foi alterado durante esta preservação; nenhuma migration
foi aplicada ao banco do aplicativo. Merge depende da aprovação do Product Owner.

## Backups privados

- `backups/sincronizacao-20260921-071624`: histórico Git e 13 worktrees,
  incluindo alterações pendentes, com verificação ZIP e hashes SHA-256.
- `backups/agro-ai-pro-2026-09-21-071614-809186`: banco PostgreSQL, código e uploads,
  com integridade e hashes registrados no manifesto.

Backups permanecem locais, ignorados pelo Git.
