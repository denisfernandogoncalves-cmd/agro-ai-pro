# Cargas colhidas — descontos acumulados após umidade (19/09/2026)

Regra confirmada pelo Product Owner com exemplo de planilha: 1.000 kg,
umidade 13%, impureza 1% e avariados 1% resultam em 980 kg e 16,33 sacas.
A umidade usa a tabela cadastrada por cultura. Impureza e avariados acumulam
sobre a mesma base após a umidade. Tolerância padrão zero e taxa padrão 1.
Regras opcionais explícitas continuam disponíveis. O campo da API
`defeitos_percentual` permanece compatível; na tela aparece como Avariados.
Snapshot v2 registra base após umidade e desconto conjunto de classificação.
Cargas históricas não foram recalculadas; nenhuma migration foi necessária.

## Arquivos da entrega

- backend/apps/graos/cargas_services.py: etapas de cálculo e snapshot.
- backend/apps/graos/serializers.py: desconto integral por padrão em novas cargas.
- backend/apps/graos/test_cargas_colhidas.py: exemplo, ordem, limites e saldo via API.
- frontend/src/pages/CargasColhidas/CargasColhidasPage.tsx: prévia, padrões e rótulos.
- frontend/scripts/test-components.mjs: regressões da prévia.
- docs/api/CARGAS_COLHIDAS.md: fórmula e compatibilidade.

## Validação

- No diretório backend: `python manage.py test --settings=config.settings.test --noinput`: 410 testes, OK, 36 skips (SQLite).
- `python manage.py makemigrations --check --dry-run --settings=config.settings.test`: sem alterações.
- Frontend: `npm test`: 42 testes de componentes e 13 cenários de autenticação aprovados.
- `npm run build` e `docker compose -p agro-ai-pro build frontend`: aprovados.
- Docker: `manage.py check` sem problemas; `manage.py migrate --check` aprovado.
- Interface recriada na porta 5174; quatro serviços healthy; HTTP 200 e API health ok.
- Revisão do diff e `git diff --check`: aprovados.
- Aviso preexistente de bundle maior que 500 kB; não há script lint.
- Suíte PostgreSQL não executada nesta entrega. Não houve teste visual autenticado.

## Preservação e Git

Backup verificado antes das alterações: `D:/PROJETOS/AGRO-AI-PRO/backups/agro-ai-pro-2026-09-19-075520-370132`.
Contém código, uploads, dump PostgreSQL, estado Git, diff e hashes SHA256.
Branch de execução: `codex/grupos-propriedades-colheita` em `.worktrees/runtime-origin-main`.
Alterações anteriores foram preservadas. Sem commit, push ou merge nesta entrega.
