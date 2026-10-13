# Recuperação do aplicativo local — 01/10/2026

Branch: `feature/importacoes-confirmacao-v1`. Repositório inicialmente limpo.

Sintoma: aplicativo em `http://127.0.0.1:5174/` sem carregar dados.
Os quatro contêineres do projeto `agro-ai-pro` estavam parados com código 255.
A causa da parada original não foi determinada. Na retomada, iniciar frontend
e backend juntos fez o Nginx sair porque o nome `backend` ainda não resolvia.

Backup privado e ignorado pelo Git:
`backups/sincronizacao-20261001-073726/`. Inclui histórico Git verificado,
código dos 13 worktrees, alterações locais, configuração privada e uploads.
O PostgreSQL parado foi copiado integralmente para `postgres-data/`;
7.947 arquivos tiveram tamanho e SHA-256 registrados em `manifesto-postgres.json`.
Os arquivos do código têm hashes no `manifesto.json` e os ZIPs foram verificados.

Recuperação: `docker compose -p agro-ai-pro start postgres redis`, seguida
da inicialização do backend e, depois de disponível, do frontend.
Nenhum volume foi recriado ou restaurado. O comando existente de inicialização
do backend executou migrations e informou que não havia migrations a aplicar.

Critérios de aceite verificados:

- Interface, API direta e `/api/health/` pelo proxy da interface: HTTP 200.
- Consulta autenticada de `/api/propriedades/` com APIClient: HTTP 200,
  retornando as três propriedades existentes no banco. Não foi testada a sessão
  particular do navegador do usuário.
- `docker compose -p agro-ai-pro exec -T -w /app/backend backend python manage.py check`:
  sem problemas.
- Mesmo comando com `makemigrations --check --dry-run`: nenhuma mudança detectada.

Não houve alteração de código, modelos ou migrations. Build e suíte completa
não foram executados porque a intervenção consistiu em retomar os serviços existentes.
Não houve commit, push ou merge. Atualizar a página no navegador para retomar o uso.
