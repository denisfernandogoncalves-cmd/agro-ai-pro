# Sincronização GitHub — 28/09/2026

Pedido do Product Owner: sincronizar no GitHub. Escopo: preservar e enviar as
alterações locais da pasta principal e da cópia que atende a porta 5174, em suas
branches atuais, sem merge, rebase, force-push ou alteração funcional adicional.

Branches: feature/importacoes-confirmacao-v1 (filtros financeiros) e
codex/propriedades-impressao-a4-20260921 (aplicativo local: usuários, financeiro,
estoque, layout, impressão e totais de propriedades).

Backup anterior ao Git: backups/sincronizacao-20260928-072452, com histórico,
13 worktrees, mudanças não commitadas e uploads, ZIPs verificados e SHA-256 no
manifesto. Banco físico parado preservado nesta sessão em
backups/sincronizacao-20260928-072224/postgres-data, com postgres-hashes.json.
Backups, uploads, banco e arquivos .env não fazem parte do envio.

Validações da pasta principal:
- npm.cmd test: 15 testes de componentes e 13 cenários de autenticação aprovados.
- npm.cmd run build: aprovado.
- manage.py test apps.financeiro --settings=config.settings.test --noinput:
  bloqueado por dependência preexistente de graos.0002 para cadpro.0001_initial.
- git diff --check: aprovado.

A sincronização preserva o código existente e não representa aprovação de uma
nova Sprint. Limitações anteriores não foram corrigidas por esta tarefa de Git.
Nenhuma migration foi aplicada nem dado do aplicativo modificado nesta tarefa.
