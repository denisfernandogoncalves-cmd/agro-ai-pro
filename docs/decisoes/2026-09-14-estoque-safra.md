# Safra na compra de estoque

Branch: `codex/grupos-propriedades-colheita`, checkout `.worktrees/runtime-origin-main`.
Alterações locais anteriores preservadas.

Campo Safra adicionado após Cultura, no formulário e na tabela, com exemplo
2026. Texto opcional de até 20 caracteres, gravado em `MovimentacaoEstoque.safra`
e retornado na API de compras. Busca considera safra. Sem alteração de models
ou migration, aproveitando o campo existente.

Assinaturas sem safra preservam compatibilidade com reenvios anteriores.
Informar outra safra para a mesma chave retorna conflito sem duplicar estoque.

Arquivos: `backend/apps/estoque/compras.py`, `test_compras.py`,
`frontend/src/api/estoque.ts`, `frontend/src/pages/Estoque/ComprasEstoque.tsx`,
`docs/api/ESTOQUE.md` e este relatório.

Backup inicial verificado: `backups/agro-ai-pro-2026-09-14-123651-119376`.
Inclui código, uploads e PostgreSQL; seis arquivos com SHA256 em manifesto,
CRC dos ZIPs e leitura integral do dump sem restauração.

Validação: 52 testes de Estoque/Relatórios aprovados com
`manage.py test apps.estoque apps.relatorios --settings=config.settings.test --noinput`;
`makemigrations --check --dry-run` sem mudanças; `npm.cmd test` com 40 testes de
componentes e 13 cenários de autenticação aprovados; `npm.cmd run build` aprovado;
`git -c core.safecrlf=false diff --check` aprovado. Aviso preexistente de bundle
acima de 500 kB permanece. Não há script lint disponível.

Atualização local pendente: Docker deixou de responder; log do backend Docker
registrou encerramento por espaço insuficiente em C:. Cerca de 400 MB livres
na verificação. Novo backup anterior à atualização ainda não foi verificado.
Nenhum backup, volume ou dado foi excluído. Sem commit, push ou merge.
