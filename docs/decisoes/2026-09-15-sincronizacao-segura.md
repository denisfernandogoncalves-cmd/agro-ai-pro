# Sincronização segura da versão local — 15/09/2026

## Objetivo e escopo

Publicar a versão em uso no computador, preservando todas as alterações locais.
Base: commit `489f66a`, checkout `.worktrees/runtime-origin-main`, branch
`codex/grupos-propriedades-colheita`. A base contém a main remota `bd6c274`
mais dez commits, já publicados na branch `codex/remover-grupos-colheita`.

A preparação e validação ocorreram na cópia isolada
`.worktrees/sincronizacao-segura-20260915`, branch
`codex/sincronizacao-segura-20260915`. Foram copiados e conferidos por SHA256
473 arquivos de código/documentação; o diff contém 37 arquivos modificados e
52 novos, além deste relatório. Sem substituição do banco ou dos uploads.

Inclui compras em estoque, boletos e parcelamentos financeiros, confirmação
de importações, grupos de propriedades, ajustes de telas/relatórios,
instalador Windows e scripts locais. Oito migrations novas fazem parte do
pacote; nenhuma migration foi executada no banco do usuário nesta tarefa.

## Preservação

- `backups/sincronizacao-20260915-062453` na raiz principal: histórico Git em
  bundle validado, arquivos das 12 worktrees em ZIP com CRC verificado,
  patches, estados Git e manifesto com hashes SHA256.
- `backups/agro-ai-pro-2026-09-15-062421-028960` no runtime: dump PostgreSQL,
  catálogo, código, uploads e diff; dump lido integralmente por pg_restore
  sem restauração, CRC dos ZIPs e SHA256 registrados.
- Diferenças da raiz principal e de `cadpro-v1` permanecem em suas cópias
  originais e no backup. Não foram sobrepostas ao aplicativo.
- A cópia em execução foi conferida contra o manifesto antes do commit.
- Banco, uploads, backups, dependências instaladas e executáveis gerados não
  integram a seleção de arquivos para publicação.

## Validação

- `manage.py check --settings=config.settings.test`: nenhum problema.
- `manage.py makemigrations --check --dry-run --settings=config.settings.test`:
  nenhuma alteração faltante.
- `manage.py test --settings=config.settings.test --noinput`: 406 testes,
  aprovado com 36 skips.
- PostgreSQL 17: suíte completa em projeto Docker isolado
  `agro-sync-qa-20260915`, sem portas expostas e sem volumes do aplicativo:
  406 testes aprovados com 5 skips; banco de teste preservado.
- `npm ci --no-audit --no-fund`, `npm test` e `npm run build`: aprovados;
  40 testes de componentes e 13 cenários de autenticação.
- `install/windows/build.py`: instalador compilado, 367 arquivos empacotados.
- Parser PowerShell: scripts sem erros de sintaxe.
- `git diff --cached --check`: aprovado; lista de publicação revisada.
- Busca de padrões de tokens conhecidos/chaves privadas: nenhuma ocorrência.
- Aplicativo existente na porta 5174: HTTP 200 e API health com status ok.

## Limites e publicação

O aviso de bundle frontend maior que 500 kB permanece. Não há script lint
definido no package.json. O instalador foi compilado, mas não instalado nesta
tarefa. Não houve auditoria exaustiva de regras de negócio.

O envio é feito em nova branch, sem force push. A cópia local em execução
deve apontar para o mesmo commit e acompanhar essa branch remota após a
verificação de igualdade da árvore Git. A main permanece sujeita à revisão
do PR e autorização explícita de merge do Product Owner.
