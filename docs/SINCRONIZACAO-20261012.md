# Sincronização com GitHub — 12/10/2026

Checkpoint das alterações locais existentes na branch `codex/modernizacao-visual`,
solicitado pelo Product Owner. Inclui interface, coordenadas GMS, histórico de
insumos, fontes do instalador Windows e sincronização offline experimental.
Não representa aprovação funcional nem integração com `main`.

Backup privado: `backups/visual-20261012-223842-909166`, com código, alterações
não commitadas, uploads e banco PostgreSQL. ZIP e catálogo do dump verificados;
tamanhos e hashes SHA-256 registrados em `manifesto.json`. Backup e dados
persistentes não são enviados ao GitHub.

## Verificações

- `git diff --check`: aprovado.
- Django `check --settings=config.settings.test`: aprovado.
- `npm test`: 15 testes de componentes e 13 cenários de autenticação aprovados.
- Scripts `test-shell.mjs`, `test-coordenadas.mjs` e `test-offline.mjs`: aprovados.
- Django `makemigrations --check --dry-run` e testes de propriedades/importações:
  bloqueados pela dependência preexistente de `graos.0005` em
  `cadpro.0001_initial`, ausente nesta árvore.
- `npm run build`: bloqueado pelo acesso ao `tsconfig.tsbuildinfo` e pelas
  referências ausentes a `components/AcoesContext` e `api/usuarios` no módulo
  offline. Os arquivos experimentais dependem de componentes de outra árvore.

Nenhuma migration aplicada, dado alterado ou merge realizado nesta tarefa.
As pendências acima devem ser resolvidas antes de integrar ou implantar este
checkpoint. Outras worktrees não estão incluídas nesta sincronização.
