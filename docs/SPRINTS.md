# Sprints — AGRO-AI-PRO

Este documento detalha o índice operacional de `documentos/SPRINTS.md`. Uma
Sprint somente é concluída quando seus critérios de aceite e validações
aplicáveis estão atendidos.

## Legenda

- `[x]` concluída e validada;
- `[~]` parcialmente implementada;
- `[ ]` pendente;
- `[!]` bloqueada.

## Sprint 1 — Infraestrutura + Propriedades

**Status:** `[x]` — concluída em 25/07/2026

- [x] backend Django, PostgreSQL e Redis em Docker;
- [x] autenticação JWT;
- [x] CRUD REST e interface de propriedades;
- [x] busca, ordenação e validações;
- [x] upload KML seguro e mapa;
- [x] proteção de propriedades com talhões vinculados;
- [x] migrations, testes e documentação validados.

Detalhes em `docs/sprints/SPRINT-01.md`.

## Sprint 2 — Talhões

**Status:** `[x]` — concluída em 25/07/2026

- [x] CRUD REST autenticado e interface dedicada;
- [x] vínculo com propriedade e integridade das áreas;
- [x] cultura, safra e dados topográficos;
- [x] produtividade esperada e realizada;
- [x] histórico agronômico;
- [x] upload KML e dados preparados para o mapa;
- [x] busca, filtros, ordenação e paginação;
- [x] migrations, testes e documentação validados.

Detalhes em `docs/sprints/SPRINT-02.md`.

## Sprint 3 — Geoprocessamento

**Status:** `[x]` — concluída em 25/07/2026

- [x] validação e armazenamento seguro de KML;
- [x] Polygon e MultiPolygon em GeoJSON;
- [x] centroide cartesiano para visualização;
- [x] tratamento de erros de leitura e geometria;
- [x] cálculo geodésico aproximado da área em hectares;
- [x] comparação entre área calculada e declarada;
- [x] renderização completa de geometrias complexas no frontend;
- [x] estratégia formal de precisão e sistema de referência;
- [x] auditoria funcional e critérios de aceite.

Detalhes em `docs/sprints/SPRINT-03.md`.

## Resumo das Sprints

| Sprint | Escopo | Status |
| --- | --- | --- |
| 4 | Clima | `[x]` — concluída em 25/07/2026 |
| 5 | Mercado | `[x]` — concluída em 25/07/2026 |
| 6 | Financeiro | `[x]` — concluída em 25/07/2026 |
| 7 | Estoque | `[x]` — concluída em 25/07/2026 |
| 8 | Operações | `[x]` — concluída em 25/07/2026 |
| 9 | Máquinas | `[x]` — concluída em 25/07/2026 |
| 10 | Relatórios | `[x]` — concluída em 25/07/2026 |
| 11 | Inteligência Artificial | `[x]` — concluída em 25/07/2026 |
| 12 | Aplicativo | `[x]` — concluída em 25/07/2026 |

A conclusão funcional das Sprints não substitui a auditoria de prontidão para
produção, acompanhada separadamente em `docs/auditoria/`.

Detalhes das Sprints concluídas ficam em `docs/sprints/`.

## Regra de execução

Quando uma tarefa não indicar Sprint específica, o agente deve:

1. ler `AGENTS.md` e o Prompt Mestre;
2. usar `documentos/SPRINTS.md` como índice operacional;
3. identificar a primeira Sprint ainda não concluída;
4. implementar uma entrega testável e compatível com o escopo;
5. atualizar os documentos somente com evidências;
6. nunca fazer commit, push ou merge sem a autorização aplicável.
