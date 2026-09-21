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

## Sprints pendentes

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

Implementações preexistentes e isoladas nesses módulos não alteram o status de
uma Sprint sem auditoria formal dos respectivos critérios de aceite.

Detalhes das Sprints concluídas ficam em `docs/sprints/`.

## Regra de execução

Quando uma tarefa não indicar Sprint específica, o agente deve:

1. ler `AGENTS.md` e o Prompt Mestre;
2. usar `documentos/SPRINTS.md` como índice operacional;
3. identificar a primeira Sprint ainda não concluída;
4. implementar uma entrega testável e compatível com o escopo;
5. atualizar os documentos somente com evidências;
6. nunca fazer commit, push ou merge sem a autorização aplicável.

## Incremento — Grupos de propriedades para colheita

**Status:** `[x]` — implementado e validado em 07/09/2026.

- Cadastro e edição em Talhões, com propriedades e CAD/PROs compartilhados ou diferentes.
- Preenchimento opcional em Cargas colhidas, preservando seleção manual e rateio proporcional.
- Migration aditiva aplicada localmente; testes de API, frontend e rateios aprovados.
- Evidências, comandos e limitações em `docs/api/GRUPOS_PROPRIEDADES_COLHEITA.md`.

## Incremento — Confirmação de importações no domínio atual

**Status:** `[x]` — implementado e validado em 07/09/2026.

- Interface de prévia, revisão paginada e confirmação explícita com permissão.
- Associação à propriedade produtora e validação do CAD/PRO atual.
- Confirmação atômica, idempotência e proteção de hashes confirmados no banco.
- Validação conjunta com grupos e cargas: 366 testes na suíte SQLite
  (36 ignorados), 48 testes direcionados no PostgreSQL, testes do frontend e build.
- Migrations aplicadas e aplicativo local saudável. Limitações e evidências
  finais em `docs/decisoes/2026-09-07-importacoes-grupos.md`.
## Incremento — Estoque por embalagens e tabela de compras

**Status:** `[x]` — implementado e validado em 14/09/2026.

- Formulário e tabela com os 12 campos aprovados; Produtor excluído.
- Vencimento de pagamento separado da validade; quantidade e valores calculados.
- Compra e entrada atômicas, reenvio protegido contra duplicação; dados antigos preservados.
- 50 testes aprovados em SQLite e PostgreSQL, frontend e build aprovados; migration aditiva aplicada e tela conferida no navegador.
- Evidências e limitações em `docs/decisoes/2026-09-14-estoque-compras-embalagens.md`.

## Correção — Descontos acumulados de cargas colhidas

**Status:** `[x]` — validada em 19/09/2026.

- Umidade pela tabela, seguida de impureza e avariados acumulados sobre o peso restante.
- Desconto integral por padrão; histórico preservado e snapshot de cálculo versionado.
- Exemplo do Product Owner: 1.000 kg, 13% de umidade, 1% de impureza e 1% de avariados = 980 kg.
- Evidências e limites: `docs/decisoes/2026-09-19-cargas-descontos-acumulados.md`.

## Incremento — Estoque disponível por fornecedor e data

**Status:** `[x]` — validado em 19/09/2026, execução agendada às 12:23.

- Consulta de saldo atual por fornecedor, produto e data de compra/entrada.
- Preço médio ponderado pela quantidade, com filtros e resumo por fornecedor.
- Sem alterações históricas; lotes com várias datas explicitados sem presumir consumo.
- Evidências: `docs/decisoes/2026-09-19-estoque-disponibilidade.md`.
