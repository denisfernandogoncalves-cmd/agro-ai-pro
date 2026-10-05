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

## Incremento — Edição, exclusão e acessos de usuários

**Status:** `[x]` — escopo validado em 01/10/2026.

- Administração de contas e seleção dos 17 módulos, com autorização central nas APIs.
- Exclusão lógica preservando históricos, bloqueio do próprio usuário e proteção de administradores.
- Migration aditiva aplicada; 41 testes direcionados no PostgreSQL, testes do frontend e build aprovados.
- Suíte completa apresentou quatro falhas fora desse escopo; detalhes, arquivos e limitações em `docs/decisoes/2026-10-01-usuarios-edicao-exclusao-acessos.md`.

## Auditoria — Telas, autenticação e usuários

**Status:** `[x]` — auditoria e correções confirmadas em 01/10/2026; recomendações de reformulação implementadas no incremento seguinte após autorização.

- Navegação autenticada pelos 17 módulos e Usuários; revisão de legibilidade, organização e adaptação ao celular.
- Corrigidos renovação de sessão em consultas de acessos, administrador revogado durante requisição, mensagens acessíveis e grades que ultrapassavam a tela.
- As quatro falhas anteriores foram resolvidas: suíte SQLite com 462 aprovações e 39 testes ignorados; 67 testes direcionados no PostgreSQL e revalidação final de accounts/core com 42 aprovações.
- Frontend, 14 cenários de autenticação e build aprovados. Evidências, backup, prioridades e limites em `docs/decisoes/2026-10-01-auditoria-telas-usuarios.md`.


## Incremento — Organização e legibilidade das telas

**Status:** `[x]` — melhorias autorizadas após auditoria, validadas e aplicadas localmente em 02/10/2026.

- Menu em seis áreas, cadastros recolhíveis, filtros avançados e resumo dos filtros aplicados.
- Datas brasileiras, textos secundários maiores, avisos de processamento e proteção contra cliques repetidos nos fluxos ajustados.
- Busca de usuários e seleção de permissões individual, por área ou de todos os módulos.
- Testes do frontend e 14 cenários de autenticação, build, checks Django e 23 testes direcionados de acesso aprovados; nenhuma migration neste incremento.
- Conferência autenticada nas larguras 360/768/1366 px; código, banco e uploads respaldados. Evidências, arquivos, comandos e limites em `docs/decisoes/2026-10-01-melhorias-telas.md`.


## Incremento — Painel, alertas, ações, histórico e favoritos

**Status:** `[x]` — melhorias autorizadas, retomadas às 12h15 e aplicadas localmente em 02/10/2026.

- Painel por módulos consultáveis, alertas de conferência, consultas por atalho e adaptação à tela.
- Ações por módulo na API/interface, histórico administrativo com diferenças persistidas e favoritos privados por conta.
- Carregamento de páginas e mapa sob demanda; aproximadamente 210 KB de JavaScript inicial.
- Embalagens automáticas arredondadas para cima e editáveis: 14,4 l / galão de 5 l = 3, com recálculo e preservação manual conferidos.
- Migrations aditivas aplicadas; suíte PostgreSQL de 515 testes, SQLite final de 516 testes, 53 testes finais direcionados, frontend e build aprovados; ignorados explicitados no relatório.
- Backup completo verificado, alterações anteriores preservadas, sem commit/push/merge. Evidências, arquivos, comandos e limites em `docs/decisoes/2026-10-02-painel-alertas-acoes-historico.md`.

## Incremento validado — 03/10/2026

Conferência de saldos, simulação, estorno com motivo, conciliação manual, rascunhos privados, preferências de relatórios e backup semanal verificado concluídos nos limites documentados. Editar/excluir transferências CAD/PRO, prévia de exclusão de cargas e Cultura em Nova venda concluídos. Validação: 540 casos backend (500 aprovados, 40 skips), 34 PostgreSQL, frontend/TypeScript/build aprovados, migrations consistentes e revisão visual responsiva. Referências: docs/decisoes/2026-10-02-conferencia-simulacao-conciliacao.md e docs/decisoes/2026-10-02-transferencias-editar-excluir.md. GitHub autorizado; merge e produção dependem de autorização específica.

## Incremento — Busca, filtros e confirmações compactas

**Status:** implementação e testes aprovados em 03/10/2026; conferência visual final do aviso de saída e telas menores pendente por bloqueio do navegador integrado.

Seis melhorias autorizadas implementadas: busca numérica, filtros rápidos, comparação de edição, proteção contra perda de alterações, motivos de bloqueio e confirmações compactas. Frontend/TypeScript/build aprovados; serviço local atualizado. Escopo e limitações: `docs/decisoes/2026-10-03-busca-filtros-confirmacoes.md`.

## Incremento — Documentos, exportação e backup Excel

**Status:** `[x]` — aplicado localmente em 03/10/2026 nos limites documentados.

Backup Excel administrativo, relatórios Excel filtrados, documentos privados auditados, avisos de duplicidades, histórico filtrável, percentuais brasileiros e renovação antecipada implementados. Migration core0003 aditiva; dados existentes preservados. Backend completo: 552 casos (512 aprovados, 40 skips), 21 PostgreSQL; frontend, TypeScript e build aprovados. Conferência visual de backup e renovação; responsividade 360/768/1366 px. Aviso compacto de saída validado em 360 px, encerrando a pendência visual anterior desse aviso. Referência: `docs/decisoes/2026-10-03-documentos-excel.md` e `docs/api/DOCUMENTOS_EXCEL.md`. Excel é consulta, não restauração; download em disco do navegador integrado não confirmado. Merge/produção não autorizados.

## Incremento — Favoritos completos de consultas

**Status:** implementação aplicada localmente e testes aprovados em 05/10/2026; conferência visual autenticada pendente por ausência de sessão válida no navegador.

Cargas e transferências salvam busca, histórico, cultura, safra e propriedade nos favoritos privados. Favoritos antigos preservados; exclusão com confirmação compacta; percentual da simulação em pt-BR. 42 testes core PostgreSQL, frontend/TypeScript/build e consistência de migrations aprovados. Sem migration ou mudança de registros operacionais. Detalhes: `docs/decisoes/2026-10-05-favoritos-consultas.md`.


## Incremento — Resumos e comprovantes individuais

**Status:** aplicado localmente em 05/10/2026; testes e conferência autenticada aprovados nos limites registrados.

Cargas, vendas e transferências recebem filtros por período, totais ativos, ordenação, detalhes recolhíveis, validação acessível e comprovantes individuais HTML/imprimíveis. Frontend/TypeScript/build, 42 core PostgreSQL e migrations consistentes. Responsividade conferida em 360/768/1366 px. Download final e diálogo nativo de impressão não confirmados; sem alteração de dados operacionais. Detalhes: docs/decisoes/2026-10-05-resumos-comprovantes.md.


## Incremento — Romaneio de venda e produção de terceiros

**Status:** aplicado e validado localmente em 05/10/2026 nos limites documentados.

Romaneio por saída de venda e recebimentos/retiradas de terceiros separados do ledger próprio e das médias das propriedades. Estoque físico/capacidade incluem terceiros; painel distingue saldos. Migration graos0015 aditiva aplicada após backup com restauração verificada. Suíte PostgreSQL 560 casos (555 aprovados, 5 skips), 105 direcionados, frontend/TypeScript/build e migrations consistentes. Conferência autenticada de formulários/romaneio; persistência de terceiros testada em banco isolado. Impressão nativa/download final não confirmados. Referência: docs/decisoes/2026-10-05-romaneio-terceiros.md.
