# Melhorias autorizadas após auditoria das abas web — 10/10/2026

## Objetivo e critérios de aceite

Versão web local `http://127.0.0.1:5174/`, checkout `.worktrees/runtime-origin-main`, branch `codex/modernizacao-visual-runtime`. Preservar as alterações anteriores, formulários, dados operacionais, permissões e documentos de duas vias.

- Consultar entradas próprias e de terceiros conjuntamente, sem apresentar lista incompleta como consulta concluída.
- Separar carregamento, erro, período inválido e consulta concluída sem resultados.
- Paginar as consultas de romaneios no banco; manter contagem e peso ativo referentes a todos os resultados filtrados.
- Preservar busca por número/CAD/PRO, busca sem acentos, datas da entrada/saída e histórico sem somar cancelados.
- Consultar somente com a aba ativa; cancelar requisições anteriores e descartar respostas atrasadas.
- Mostrar filtros ativos e horário de conclusão da consulta; preservar filtros ao alternar abas.
- Validar testes, compilação, migrations e interface autenticada desktop/móvel antes de encerrar.

## Implementação

Dois endpoints de leitura, sem substituir as listagens usadas por outros fluxos:

- `GET /api/graos/cargas-colhidas/romaneios/`: acesso de consulta a Cargas; união de chaves de cargas próprias e entradas de terceiros ordenada/paginada no banco. Hidratação dos registros somente da página. Busca nos nomes/CAD/PROs preservados no snapshot da carga. Culturas disponíveis obtidas com `DISTINCT`.
- `GET /api/comercial/romaneios/`: acesso de consulta a Vendas; consulta paginada das saídas, com dados comerciais suficientes para o documento e sem carregar todas as entregas/devoluções/históricos de cada venda.

Parâmetros comuns: `busca`, `inicio`, `fim`, `historico`, `pagina`, `por_pagina` (5/10/20), `ordem` (recentes/antigos). Entradas também aceitam `origem`, `cultura`, `terceiro`. Datas e limites são validados no servidor. Página acima da última retorna a última página disponível.

Resposta: `itens`, `total`, `pagina`, `paginas`, `por_pagina`, `inicio`, `fim`, `peso_ativo_kg`, `consultado_em`; entradas incluem `culturas`. Total e peso usam todos os registros filtrados, independentemente da página. Histórico não entra no peso ativo; devoluções não são abatidas do total bruto das saídas, conforme a legenda existente.

As duas telas reutilizam `useConsultaRomaneios`: espera de 250 ms para agrupar alterações de filtros, `AbortController`, proteção contra respostas antigas e suspensão em abas ocultas/períodos invertidos. A atualização de entradas usa uma única resposta com ambas as origens, eliminando a coordenação de duas consultas HTTP independentes. Impressão/download continuam usando os componentes e endpoints existentes.

## Arquivos

- Backend: `apps/core/consulta_romaneios.py`, `apps/graos/consulta_romaneios.py`, `apps/vendas/consulta_romaneios.py`, URLs dos dois módulos e seus `test_consulta_romaneios.py`; preparação de fixtures históricas em `apps/graos/test_migration_0006.py` e `test_migration_0009.py`.
- Frontend: `src/api/romaneios.ts`, páginas Cargas/ListaRomaneiosEntrada, Vendas/LocalizadorRomaneios/RomaneioVenda, `src/utils/datas.ts`, `scripts/test-romaneios.mjs`, `scripts/test-usabilidade.mjs`.
- Documentação: este registro e `docs/SPRINTS.md`.

## Backups

Pasta privada ignorada pelo Git, com código inclusive não commitado, uploads e dump PostgreSQL. ZIPs verificados por CRC, dump lido integralmente por `pg_restore`, hashes SHA256 e conteúdo registrados em `manifesto.json`:

- Antes das alterações: `backups/agro-ai-pro-2026-10-10-140508-216275`.
- Antes da atualização local: `backups/agro-ai-pro-2026-10-10-141557-871653`.

Nenhuma restauração, migration ou alteração de registro operacional foi necessária. Sem commit, push, merge ou publicação em produção.

## Verificações

- Sete novos testes PostgreSQL isolado aprovados: paginação, totais globais, filtros, histórico, nomes preservados, validação e acesso.
- `docker compose -p agro-ai-pro build frontend`: `npm test`, testes comportamentais das consultas/abas, TypeScript e Vite aprovados.
- Django `check`: sem problemas; `makemigrations --check --dry-run`: sem mudanças.
- Frontend da porta 5174 atualizado e saudável.
- Navegador autenticado: entradas com quatro registros e 191.363,4 kg; busca por 58 com um registro e 48.510 kg; consulta vazia válida; filtros preservados ao alternar abas; períodos invertidos em entradas/saídas apresentam alerta e ocultam total/lista/contador; saídas com um romaneio e 37.500 kg. Conferência móvel em 360 px sem transbordamento horizontal. Filtros de conferência limpos ao finalizar; nenhum formulário operacional salvo.
- `docker compose -p agro-ai-pro exec -T backend python /app/scripts/test_backend_isolado.py apps.graos apps.vendas apps.accounts`: 347 casos, 340 aprovados, cinco ignorados e dois erros em fixtures antigas de migrations. A causa era o estado de Propriedade fixado em 0004, divergente da migration 0005 já aplicada no banco temporário. Corrigidos somente os testes para usar o estado das migrations efetivamente aplicadas; nenhuma migration antiga ou modelo alterado.
- Reteste `... test_backend_isolado.py apps.graos.test_migration_0006 apps.graos.test_migration_0009`: dois testes aprovados. Os demais casos já aprovados não foram repetidos, pois a correção se limita à preparação desses dois testes.
- Revisão do diff comparando o checkout ao ZIP anterior à tarefa; `git diff --check` sem erros. Nenhuma dependência adicionada.

## Limites

Paginação aplicada às abas de romaneios. As listagens principais de Cargas próprias e Vendas registradas continuam com o contrato existente; não se declara paginação integral desses módulos nem teste de carga em grande volume. A busca de snapshots usa JSONB do PostgreSQL oficial do projeto. Impressão física e download final em disco não executados nesta etapa.
