# Estoque por fornecedor e data da compra — 19/09/2026

Execução agendada para 12:23, America/Sao_Paulo. Objetivo: consultar saldo
por fornecedor/data de compra e média ponderada do preço de aquisição.
Branch: codex/grupos-propriedades-colheita; checkout runtime-origin-main,
confirmado pelo volume /app do backend no Docker.

## Critérios e resultado

Consulta autenticada somente leitura, filtros por produto/fornecedor/período,
saldo atual conciliado com a posição existente, detalhes por data e resumo por
produto/fornecedor. Preços em R$ por unidade, ponderados pelas quantidades
compradas; valores de compras em embalagens respeitam seu total original.
Lotes com várias datas não têm consumo por compra inventado: uma linha com
datas múltiplas e saldo conjunto. Regra e limitações na documentação da API.
Dados históricos e alterações locais anteriores preservados; nenhuma migration.

## Arquivos

Novos: backend/apps/estoque/disponibilidade.py,
backend/apps/estoque/test_disponibilidade.py,
frontend/src/pages/Estoque/DisponibilidadeEstoque.tsx e este relatório.
Alterados: backend/apps/estoque/urls.py, frontend/src/api/estoque.ts,
frontend/src/pages/Estoque/EstoquePage.tsx, frontend/scripts/test-components.mjs,
docs/api/ESTOQUE.md e docs/SPRINTS.md.

## Preservação

Backup verificado: D:/PROJETOS/AGRO-AI-PRO/backups/agro-ai-pro-2026-09-19-122348-333824.
Código, uploads, dump PostgreSQL, catálogo, diff e estado Git; CRC e SHA256,
leitura integral do dump sem restauração. Sem commit, push ou merge.

## Validação

- `python backend/manage.py test apps.estoque --settings=config.settings.test --noinput`: 40 testes aprovados, incluindo 8 da consulta nova.
- `manage.py check` e `makemigrations --check --dry-run`: aprovados, sem migrations pendentes de criação.
- `npm test`: 44 testes de componentes e 13 cenários de autenticação aprovados.
- `npm run build` e build Docker frontend: aprovados.
- Conciliação somente leitura no PostgreSQL real: três grupos e três resumos, todos os saldos coincidem com posicao_estoque.
- Docker: check e migrate --check aprovados; quatro serviços healthy.
- HTTP 200 em 127.0.0.1:5174 e API health ok.
- Diff revisado e git diff --check sem erros.

Não houve teste visual autenticado no navegador nem repetição da suíte completa
de outros módulos. Permanece o aviso conhecido de bundle frontend acima de 500 kB;
o projeto não possui script lint. A consulta percorre os movimentos dos produtos
selecionados; volumes muito grandes poderão exigir agregação/paginação futura.
