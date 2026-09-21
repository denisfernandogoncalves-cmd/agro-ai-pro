# Recuperação do acesso local — 14/09/2026

## Escopo e resultado

Restabelecer http://127.0.0.1:5174/ após liberação de espaço no C:.
Os quatro contêineres de agro-ai-pro estavam parados (código 255).
C: apresentava aproximadamente 32 GB livres. A causa exata da parada
anterior não foi determinada. Não houve alteração de código ou configuração.
Checkout utilizado: `.worktrees/runtime-origin-main`, branch
`codex/grupos-propriedades-colheita`; alterações preexistentes preservadas.

## Preservação

Executado `scripts/backup_local.py` com o Python da .venv do repositório.
Backup privado no checkout: `backups/agro-ai-pro-2026-09-14-210648-196969`.
Inclui banco físico parado, código atual, uploads, estado Git e diff.
Leitura integral de 7943 entradas do banco, CRC dos ZIPs e hashes SHA256
registrados no manifesto. Nenhuma restauração realizada.

## Recuperação e validação

- `docker compose -p agro-ai-pro start --wait --wait-timeout 120` iniciou
  banco, Redis e backend; frontend falhou porque o nome backend ainda não
  estava disponível no início do Nginx.
- `docker compose -p agro-ai-pro start --wait --wait-timeout 60 backend`
  seguido do mesmo comando para `frontend` concluiu a inicialização.
- `docker compose -p agro-ai-pro ps`: quatro serviços healthy.
- HTTP GET na porta 5174: página, JavaScript e CSS retornaram 200.
- `/api/health/` pela porta 5174: status ok, service backend.
- `docker compose -p agro-ai-pro exec -T backend python backend/manage.py check`:
  nenhum problema.
- `docker compose -p agro-ai-pro exec -T backend python backend/manage.py migrate --check`:
  aprovado, nenhuma migration pendente; nenhuma migration criada nesta tarefa.

Build e suíte funcional completa não executados: recuperação operacional dos
contêineres existentes, sem mudanças no aplicativo. Validação limitada à
disponibilidade, arquivos estáticos, saúde da API e verificações Django.
Commit, push e merge não realizados.
