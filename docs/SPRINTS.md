# Sprints — AGRO-AI-PRO

## Incremento — identificação CAD/PRO no faturamento (19/10/2026)

- [x] Principal/Secundário do cadastro na seleção, impressão e PDF; identificação preservada no resumo histórico.
- [x] Excel individual com identificação, permissão de impressão e dados do resumo confirmado.
- [x] 31 testes PostgreSQL, frontend/TypeScript/build, Django/migrations/diff, renderização de PDF e leitura de Excel aprovados.

Critérios e limites: [identificação no faturamento](decisoes/2026-10-19-identificacao-cadpro-faturamento.md).

## Incremento — aba de grupos e exclusão com histórico (19/10/2026)

- [x] Grupos retirados de Talhões e movidos para página própria em Cadastros.
- [x] Exclusão lógica com cópia histórica das áreas, consulta aos excluídos e bloqueio de alteração do histórico.
- [x] Testes PostgreSQL pertinentes e retestes, frontend/TypeScript/build, migration aditiva e readiness aprovados.

Backups, critérios e evidências: [grupos e histórico](decisoes/2026-10-19-grupos-historico.md).

## Correção — quatro casas na área de propriedades (18/10/2026)

- [x] Entrada/listagem com quatro casas em alqueires e persistência sem arredondamento para duas casas em hectares.
- [x] Migration propriedades.0009 aplicada após backup; 55 testes PostgreSQL e frontend/TypeScript/build aprovados.

Evidências e limites: [precisão da área](decisoes/2026-10-18-area-quatro-casas.md).

## Incremento — propriedades, grupos e busca geral (18/10/2026)

- [x] GMS padrão nos novos cadastros; identificação CAD/PRO, tipo do imóvel e apelido editáveis.
- [x] Seleção múltipla de propriedades com CAD/PRO individual nos grupos; busca de produto/princípio ativo.
- [x] Busca geral de registros por palavra/número com permissões, cancelamento e limites explícitos.
- [x] 29 testes PostgreSQL, frontend/TypeScript/Vite, Django/migrations/diff e readiness aprovados; atualização local em 5174.

Backups, comportamento e limites: [cadastros e buscas](decisoes/2026-10-18-cadastros-busca.md). Sem commit, push ou merge.

## Incremento — integração das novas contas a pagar (16/10/2026)

- [x] Novas despesas externas de Transportes, remunerações e manutenções concluídas integradas com título único e baixa manual.
- [x] Históricos preservados para conferência; sem duplicar consumo de diesel no silo.
- [x] Cartões de resumo do Estoque retirados e contas a pagar pendentes em vermelho.
- [x] Testes finais PostgreSQL, Django/migrations e versão ativa na porta 5174 conferidos; backup verificado.

Evidências, arquivos e limites: [integração de contas a pagar](decisoes/2026-10-16-contas-pagar-integracao.md).
Sem commit, push, merge ou produção. Históricos gerais não incorporados automaticamente.

## Incremento — compras de diesel e abastecimento no silo (15/10/2026)

- [x] Compras S10/S500 em Transportes, filtros, totais, cadastro e edição versionada.
- [x] Despesas com opção Abasteceu no silo: litros e preço da última compra
  do mesmo tipo até a data; referência e preço histórico preservados.
- [x] 102 testes PostgreSQL (um skip), auditoria adicional, frontend/testes,
  TypeScript/Vite/Docker, Django/migrations e diff aprovados. Duas migrations
  aditivas aplicadas após backup; duas compras da planilha importadas sem
  duplicação; aplicativo local atualizado na porta 5174.
- [ ] Conferência visual autenticada da tela.

Evidências e limites: [diesel e silo](decisoes/2026-10-15-diesel-silo.md).
Sem baixa automática de estoque, pagamentos, commit, push ou merge.

## Incremento — motoristas e cabeçalho do faturamento (15/10/2026)

- [x] Excluir motorista por inativação versionada, histórico preservado,
  excluídos/inativos em seção recolhível e opção de reativar.
- [x] Cabeçalho de insumos distribuído em colunas na tela/impressão/PDF,
  destacando empresa e embalagens sem aumentar as fontes.
- [x] 29 testes PostgreSQL e dois de PDF, frontend/TypeScript/build,
  Django/migrations, diff e renderização visual do PDF aprovados.
- [x] Aplicativo local 5174 atualizado; sem alteração de dados reais ou schema.

Evidências: [motoristas e cabeçalho](decisoes/2026-10-15-motoristas-cabecalho.md).
Sem conferência visual autenticada da tela, commit, push ou merge.

## Incremento — estornos de compras e ativação de armazenagem (15/10/2026)

- [x] Cancelamento total e estorno parcial em litros/kg, com motivo, responsável,
  histórico preservado, reenvio seguro, versão e proteção contra saldo insuficiente.
- [x] Sugestão de embalagens aceita dosagem decimal sem zero inicial; botão
  Ativar nas armazenagens de grãos inativas, respeitando permissão de edição.
- [x] Testes PostgreSQL de compras/estornos/concorrência/armazenagem, frontend,
  TypeScript/Vite, check e migrations aprovados; migration 0008 aditiva aplicada
  após backup. Dados originais preservados e frontend local 5174 atualizado.
- [ ] Conferência visual autenticada; não foram feitos estornos em compras reais.

Evidências e limites: [compras e armazenagem](decisoes/2026-10-15-estornos-quantidade-armazenagem.md).
Sem estorno financeiro automático, commit, push ou merge.

## Correção — impressão de faturamento (15/10/2026)

- [x] Impressão do painel ativo corrigida; total de embalagens e safra no cabeçalho.
- [x] Nome do arquivo e título PDF com produto, embalagens, safra e data, conforme exemplo do Product Owner.
- [x] 26 testes PostgreSQL, frontend/TypeScript/build e renderização de impressão/PDF aprovados.

Evidências: [impressão de faturamento](decisoes/2026-10-15-impressao-faturamento.md). Sem migration ou alteração de dados reais.

## Correção — consulta automática ADAPAR (14/10/2026)

- [x] Empresa da consulta preenche o campo fabricante/empresa registrante; frontend testado e atualizado.
- [x] Consulta online pública por registro testada: FOLICUR e Bayer S.A. em 0,86 s; integração automática online ainda não implementada.

- [x] Leitor PDF instalado na imagem e extração limitada às páginas correspondentes.
- [x] 136 testes existentes e três testes de extração aprovados em ambiente isolado.
- [x] Backend local saudável; FOLICUR retornou HTTP 200 em 6,66 s, sem alterar os 60 produtos.

Evidências: [consulta ADAPAR](decisoes/2026-10-14-consulta-adapar.md).

## Incremento — cadastro de motoristas e apelidos (14/10/2026)

- [x] Cadastro independente com apelido opcional; seleção de placa e motorista nas cargas e conferência de Transportes.
- [x] Quatro testes de motoristas, oito de fretes, frontend/TypeScript/build e Django check aprovados; migration aditiva aplicada após backup verificado.
- [ ] Conferência visual autenticada.

Detalhes: `docs/decisoes/2026-10-14-cadastro-motoristas-apelidos.md`.

## Correção — consulta de produtos (14/10/2026)

- [x] Migration aditiva 0007 aplicada após backup; 60 produtos e campos originais preservados.
- [x] 98 testes isolados, frontend/build e consulta autenticada HTTP 200 aprovados.
- [x] Falha de consulta distinguida de catálogo vazio; cadastro manual sem dependência de PDF.

Evidências: [correção de produtos](decisoes/2026-10-14-correcao-produtos.md).


## Incremento — transportes, relatórios e integração preparada (14/10/2026)

- [x] PUT/PATCH de caminhões, lançamentos e remunerações protegidos por versão.
- [x] Totais de grãos agregados no banco e detalhes paginados antes da serialização.
- [x] Integração isolada preparada sem conflitos; 807 testes backend (seis skips),
  testes frontend, TypeScript/build e migrations aprovados.
- [ ] Commit/push e conclusão da integração em main não executados.

Evidências e limites: [decisão](decisoes/2026-10-14-melhorias-integracao.md).

## Incremento — controles de editar/excluir (14/10/2026)

- [x] Ações existentes expostas em Transportes, frota, manutenções agendadas,
  operações planejadas e lotes/movimentações de estoque, respeitando os bloqueios.
- [x] 114 casos PostgreSQL (um skip), frontend/TypeScript/Vite e Django aprovados.
- [ ] Abrangência global e correção de históricos encerrados: decisão e interfaces
  adicionais pendentes; não declarar todos os campos livremente alteráveis.

Evidências e limites: docs/decisoes/2026-10-14-editar-excluir.md.

## Incremento — comissão e seleção compacta de propriedades (14/10/2026)

- [x] Base da comissão manual nas cargas usa peso bruto do produto, sem tara ou
  descontos de qualidade; valores salvos preservados.
- [x] Menu de propriedades com busca/seleção múltipla, CAD/PRO apenas das escolhidas.
- [x] Oito testes de fretes PostgreSQL e frontend/TypeScript/Vite aprovados;
  nome do motorista corrigido no registro de abril após backup.
- [x] Aba Motoristas e caminhões com edição e desvinculação do nome atual,
  preservando caminhão e histórico; 21 casos de Transportes (um skip) aprovados.
- [x] Tarifa de frete por tonelada sobre peso bruto e comissão sugerida pelo
  percentual cadastrado; valores antigos preservados, cálculo decimal testado.

Evidências e limites: docs/decisoes/2026-10-14-ajustes-operacionais.md.

## Incremento — cotações gratuitas de Chicago (14/10/2026)

- [x] Soja, milho e trigo via Yahoo Finance / CBOT; dólar pelo Investing, fontes,
  contratos, unidades, atraso e horários originais explícitos.
- [x] Cache, preservação em falhas e validação existente reutilizados; 22 testes
  de mercado, frontend/TypeScript/Vite, Django e migrations aprovados.
- [ ] Conferência visual autenticada.

Evidências, backups e limites: docs/decisoes/2026-10-14-cotacoes-gratuitas.md.
Sem migrations ou alteração de dados operacionais; sem commit/push/merge.

## Incremento — Transportes por caminhão e motorista (12/10/2026)

**Status:** `[x]` — implementado e validado na versão web local.

- Nova aba em Operações, com vários caminhões, receitas/despesas, salário e comissão
  manuais por mês, relatórios por data/motorista/placa e ranking de faturamento.
- Importação revisável e idempotente; 405 lançamentos e nove remunerações reais
  carregados após backup verificado, preservando datas e o arquivo original.
- 53 testes iniciais de Transportes/accounts e 17 finais de Transportes aprovados
  em PostgreSQL isolado; frontend, TypeScript/Vite, Django/migrations e navegador
  autenticado/móvel aprovados. Migration aditiva aplicada; frontend 5174 saudável.
- Duas receitas em FEV são datadas de 31/01 na fonte: aparecem em janeiro nos
  relatórios por data. Remuneração contabilizada no último dia da competência.

Evidências, backups, critérios e limites: `docs/decisoes/2026-10-12-transportes.md`.
Sem commit, push, merge ou produção.

## Incremento — Segunda etapa de gestão sem EXE (07/10/2026)

**Status:** `[x]` — sete melhorias implementadas e validadas localmente.

Estados reais dos documentos; checklist persistente por usuário/safra com histórico;
comprovantes financeiros vinculados; extrato por propriedade/CAD-PRO; comparação
de safras sem somar transferências externas à produção; abertura da origem exata
de pendências; adaptação dos controles ao celular.

138 testes PostgreSQL isolados, frontend/TypeScript/Vite/Docker, Django check e
consistência de migrations aprovados. Migration aditiva do checklist aplicada,
backups verificados e aplicação local atualizada. Critérios e limites:
`docs/decisoes/2026-10-07-gestao-segunda-etapa.md`.

## Incremento — Central de gestão sem EXE (07/10/2026)

**Status:** `[x]` — implementado e validado localmente nos limites documentados.

Central de documentos com busca/paginação no servidor e PDF/Excel; diagnóstico
autenticado e backup administrativo; checklist temporário com atalho para fechamento;
conferência de liquidações a menor/a maior; filtros de revisão da importação;
ajuda contextual e guia de rede local. Sem executável, migrations ou ajustes automáticos.

44 testes PostgreSQL isolado, frontend, TypeScript/Vite/Docker, Django check e
consistência de migrations aprovados. Conferência autenticada e atualização local
na porta 5174 concluídas. Acesso por outro computador e gravação final dos downloads
em disco não confirmados. Referência: `docs/decisoes/2026-10-07-central-gestao-sem-exe.md`.

## Incremento — Conferência das outras abas (07/10/2026)

**Status:** `[x]` — melhorias implementadas e testes aprovados.
Atalhos de indicadores, descontos por parcela, composição do estoque, origem e
destino, restante de vendas, diferenças financeiras, validade de lotes, áreas
divergentes e relatórios PDF/Excel. 30 PostgreSQL, frontend/TypeScript/build e
migrations consistentes. Escopo e limites:
`docs/decisoes/2026-10-07-melhorias-outras-abas.md`.

## Incremento — Clareza das transferências de terceiros (07/10/2026)

**Status:** `[x]` — seis melhorias implementadas e testes aprovados.
Botão com motivo de bloqueio, status, filtros no servidor, prévia de saldos,
comprovantes PDF/Excel e recebimentos separados da produção. 11 PostgreSQL,
frontend, TypeScript e build aprovados; sem migration. Evidências e limites:
`docs/decisoes/2026-10-07-usabilidade-transferencias-terceiros.md`.

## Incremento agendado — Conciliação e transferências externas (07/10/2026)

**Status:** `[x]` — implementado e validado localmente.
Vínculo manual de recebimentos, conciliação de estoque, proteção do ledger em
períodos fechados, histórico comparável, revisão de duplicidades, busca/páginas
no servidor e painel com prioridade/prazo opcional. Transferência de terceiros
para outro CAD/PRO preserva estoque e não soma produção, área ou produtividade.
339 testes PostgreSQL (334 aprovados, cinco skips), 23 finais e oito revalidados;
frontend/testes/TypeScript/build aprovados. Backups restaurados em isolamento,
sem nova migration nem dados fictícios operacionais. Evidências e limites:
`docs/decisoes/2026-10-07-melhorias-agendadas-cadpro.md`.

## Auditoria — Romaneios, terceiros e fechamentos (07/10/2026)

**Status:** `[x]` — revisão e correções autorizadas implementadas e validadas.
Cinco falhas reproduzidas com dados sintéticos em SQLite em memória. Frontend,
Django check, migrations e verificador de backup aprovados; serviços saudáveis.
Prioridades, evidências e limitações:
`docs/decisoes/2026-10-07-auditoria-romaneios-terceiros.md`.
Correções, testes PostgreSQL, backups e limites:
`docs/decisoes/2026-10-07-correcoes-auditoria.md`.

## Incremento — Download de romaneios de entrada (07/10/2026)

**Status:** `[x]` — PDF e Excel (.xlsx) disponíveis para cargas próprias,
compartilhadas e recebimentos de terceiros. Botões separados no comprovante
e na consulta de romaneios. PDF A4 com duas vias, pesos, descontos, qualidade,
propriedades/CAD/PRO, motorista e assinaturas; download exige impressão.
Testes de exportação e permissão, frontend e build aprovados. PDF da carga
compartilhada #57 renderizado e conferido visualmente. Backups privados
verificados antes das alterações. Detalhes no documento de decisões abaixo.

## Incremento — Cadastro, fechamentos e fila de conferência (07/10/2026)

**Status:** `[x]` — telas integradas, identidade explícita nos extratos/resumos,
fechamentos, fila auditável e comprovantes de retirada implementados.
44 testes finais relacionados aprovados em PostgreSQL, incluindo concorrência.
Validação ampla anterior: 346 testes, cinco skips, sem falhas.
Ensaio conjunto de recuperação do banco e uploads já verificado; automação
semanal existente atualizada, mantendo o horário de domingo às 06h.
Referência: `docs/decisoes/2026-10-07-cadastro-fechamento-pendencias.md`.

## Incremento — Extrato de terceiros, conferência física e backup (07/10/2026)

**Status:** `[x]` — cinco melhorias autorizadas implementadas e validadas localmente.

Extrato cronológico com saldo acumulado, aviso de duplicidade, filtros de
romaneios por produto/terceiro/período, contagem física auditável sem ajuste
automático e situação administrativa de backup completo. Migration graos0020
aditiva aplicada após backup restaurado em isolamento. 64 testes PostgreSQL
aprovados, frontend/TypeScript/build/Docker e verificação visual autenticada
aprovados. Escopo, comandos, backups e limites:
`docs/decisoes/2026-10-07-extrato-conferencia-backup.md`. Sem commit/push/merge.

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


## Incremento — Descontos de terceiros e pesagem de vendas

**Status:** implementado e validado localmente em 05/10/2026.

Terceiros identificados pelo nome, com descontos iguais às cargas próprias e prévia sem movimentação; estoque separado e médias preservadas. Vendas com bruto, tara e líquido calculado, qualidade apenas informativa no romaneio e rascunho. Filtros recolhíveis e formulários responsivos. Migrations graos0016 e vendas0009 aditivas aplicadas após backups restaurados em isolamento. Suíte PostgreSQL 563 casos (558 aprovados e 5 skips), mais 21 de ajustes finais; frontend/test/TypeScript/build aprovados. Detalhes em docs/decisoes/2026-10-05-romaneio-terceiros.md.


## Incremento — Edição de terceiros, PH por cultura e duas vias

**Status:** `[x]` — aplicado e validado localmente em 05/10/2026 nos limites documentados.

Nova venda no início; edição/exclusão por estorno de terceiros com motivo, versão, permissões e snapshots; PH somente trigo. Migration graos0017 aplicada, suíte PostgreSQL com 567 casos (562 aprovados, 5 skips), frontend/TypeScript/build aprovados. Entradas próprias/compartilhadas/terceiros e vendas imprimem duas vias na mesma folha A4, com fonte adaptável e bloqueio de transbordamento. Dados completos e escape HTML testados; conferência DOM/visual, sem impressão física. Backups restaurados em isolamento, sem modificar registros reais nos testes. Detalhes: docs/decisoes/2026-10-05-terceiros-edicao-ph.md e docs/decisoes/2026-10-05-impressao-duas-vias.md.


Refinamento visual de 05/10/2026: cabeçalho, rótulos, pesos destacados e fonte maior nas duas vias, com formato compacto adaptável para conteúdo extenso. Frontend/TypeScript/build e DOM validados; sem alteração de dados ou migrations. Referência: docs/decisoes/2026-10-05-impressao-duas-vias.md.

Correção de 05/10/2026: comprovante geral de vendas também em duas vias na mesma folha A4; prévia no topo e impressão sem margem superior do diálogo. Frontend/TypeScript/build aprovados, sem migration ou alteração operacional. Evidências em docs/decisoes/2026-10-05-impressao-duas-vias.md.

Incremento de 05/10/2026: Nova venda e documentos em duas colunas no desktop, com romaneio no topo do detalhe; uma coluna em telas menores. Frontend/TypeScript/build aprovados e conferência autenticada 360/768/1366 px sem transbordamento. Sem migration/dados alterados. Referência: docs/decisoes/2026-10-05-vendas-duas-colunas.md.


## Incremento — Localizador compacto de romaneios

**Status:** `[x]` — aplicado e validado localmente em 05/10/2026 nos limites documentados.

Consulta independente da venda selecionada, busca e período da saída, histórico e detalhes recolhidos, impressão individual de saídas anteriores. Lista compacta com cinco por página (opções dez/vinte), teste de 1.000 registros e limites de paginação. Frontend/TypeScript/build aprovados; conferência autenticada de romaneio anterior e responsividade 360/768/1366 px. Duas vias em uma folha A4 preservadas; sem migration ou alteração operacional. Referência: docs/decisoes/2026-10-05-localizar-romaneios.md.


Refinamento adicional dos impressos: estilos internos isolados do diálogo, grade de três colunas e distribuição vertical aproveitando cada metade da folha. Romaneio #48 validado em fonte 16 px e duas vias sem transbordamento; frontend/TypeScript/build aprovados. Sem migration ou dado operacional alterado. Referência: docs/decisoes/2026-10-05-impressao-duas-vias.md.


### Incremento autorizado — abas internas e espaçamento (05/10/2026)

- [x] Sete módulos com abas acessíveis, preservação de formulários/filtros e permissões; catálogo de entradas próprias/terceiros paginado.
- [x] Financeiro e Máquinas conferidos; Nova venda restrita ao cadastro; legendas e espaçamento de Cargas/Vendas corrigidos.
- [x] Testes frontend, TypeScript/Vite no Docker, backup verificado e validação visual responsiva aprovados. Impressão física/PDF nativo não realizada; duas vias A4 preservadas no DOM.

Referência: docs/decisoes/2026-10-05-abas-modulos.md. Sem alteração de dados, backend ou migrations.

### Incremento — preço negociado e modelo do romaneio de venda (05/10/2026)

**Status:** `[x]` — implementado e validado localmente.

Cadastros agrícolas agora aceitam preço opcional por kg ou saca de 60 kg. O total negociado é calculado pela quantidade líquida da saída: peso em kg × preço/kg, ou peso ÷ 60 × preço/saca; ele aparece somente na segunda via do romaneio, destinada ao arquivo. A primeira via permanece destinada ao cliente. O romaneio passou a usar a grade de conferência solicitada: Peso bruto, Tara e Peso líquido, com Sacas/60 no bloco de pesagem e qualidade na lateral; classificação padrão e nota da empresa foram removidas. Migration `vendas.0010` aditiva aplicada após backup verificado. Backend de vendas, frontend, TypeScript/Vite e testes de duas vias aprovados; detalhes em `docs/decisoes/2026-10-05-preco-romaneio.md`.

Continuação: romaneios individuais podem ser baixados em PDF ou Excel (`.xlsx`) com duas vias, PDF A4 de uma página e total restrito ao arquivo; tema da interface passou para texto preto em fundo branco. Os 83 testes de vendas (9 skips), quatro testes específicos de download, frontend, TypeScript sem incremental, build Vite e consistência de migrations passaram. Conferência visual autenticada pendente; a base persistente de testes PostgreSQL apresentou usuário duplicado e foi preservada. Detalhes em `docs/decisoes/2026-10-05-preco-romaneio.md`.

### Incremento — romaneios de entrada, tema e transferência de terceiros (06/10/2026)

**Status:** `[x]` — implementado, validado e aplicado localmente nos limites documentados.

Entradas próprias/compartilhadas/terceiros usam a grade dos romaneios de venda, com descontos e sem reais; duas vias completas na mesma folha A4, cliente primeiro. Cadastro/CAD/PRO sem peso rateado ao lado; motorista antes da placa, também em PDF/Excel de vendas. Paleta escolhida: azul petróleo, branco e cinza claro.

Terceiros podem transferir líquido para a propriedade/CAD/PRO no mesmo armazém, debitando saldo separado e creditando o ledger sem produção colhida ou mudança nas médias. Histórico imutável, versão, reenvio, permissões de ambas as áreas, bloqueios e estorno atômico com saldo livre. Migration graos0018 aditiva aplicada após backup com restauração isolada aprovada.

82 testes PostgreSQL isolado aprovados, incluindo concorrência; reforço final de reenvio/permissões aprovado em SQLite. Frontend, TypeScript/Vite/Docker, Django check, consistência de migrations e diff aprovados. Conferência autenticada de entradas e responsividade 360/768/1366 px; formulário de transferência conferido com dados fictícios sem banco real. Sem alterações operacionais reais nos testes. Impressão física e download final em disco não executados. Referências: `docs/decisoes/2026-10-06-romaneios-entrada-tema.md` e `docs/api/TRANSFERENCIAS_CORRECOES.md`. Atualização autorizada da PR 29; sem merge/produção.


### Incremento — Relatório de contas a pagar (07/10/2026)

- [x] Seção Contas a pagar em Relatórios, filtro de tipo no servidor, período por vencimento, propriedade/safra, paginação e reutilização PDF/Excel.
- [x] Teste específico e 17 testes existentes de relatórios aprovados; frontend/test/TypeScript/build aprovados. Sem migration ou alteração de lançamentos.

Referência: docs/decisoes/2026-10-07-contas-pagar.md.


### Auditoria técnica geral — 07/10/2026

- [x] Revisão de módulos, permissões, integridade, consultas, dependências e amostragem visual; 673 casos PostgreSQL isolado (668 aprovados, 5 skips), frontend/build aprovados, migrations consistentes e npm audit sem vulnerabilidades reportadas.
- [ ] Correções e melhorias identificadas: validação numérica em ações, upload coerente, paginação no banco, versões nas edições e filtros aplicáveis. Não tratadas como implementadas.

Evidências, prioridades, propostas por módulo e limites: docs/decisoes/2026-10-07-auditoria-geral.md.


### Incremento auditado — retomada de 08/10/2026

- [x] Cobertura contratual com reserva própria separada, reservas alheias, entregas parciais, cancelamento e permissões: 13 testes aprovados.
- [x] Validação numérica, referência bissexta, inativação versionada e referências antigas de CAD/PRO; relatórios financeiros/máquinas/insumos/operações com consultas paginadas; filtros financeiros aplicáveis; exportação de conferência e matriz de permissões salvas.
- [x] Fonte/data/idade de clima e mercado e proteção da troca de propriedade: frontend/test/TypeScript/build aprovados.
- [x] Backend integral: 688 casos (683 aprovados, 5 skips); Django/migrations consistentes; backups com restauração isolada.
- [x] Aplicação local saudável; dashboard/mercado/clima/contas a pagar conferidos; Clima distingue janela atual e histórico. Mercado e Clima sem extravasamento em 360 px.
- [ ] Restante das melhorias autorizadas. Escopo geral não concluído.

Evidências e limites: docs/decisoes/2026-10-08-retomada-auditoria.md.


### Incremento — CBOT em US$/bushel (08/10/2026)

- [x] Backend e interface de soja, milho e trigo com fonte, contrato, horário, conversão de US¢/bushel e atualização manual autorizada; histórico mensal separado.
- [x] 51 testes PostgreSQL, frontend e build aprovados; migration aditiva consistente, backups verificados e cotações reais carregadas; aplicação local atualizada.
- [ ] Conferência visual autenticada desktop/celular e atualização pelo botão: sessão expirada no navegador.

Evidências e limites: docs/decisoes/2026-10-08-cbot-bushel.md.


### Incremento — Investing e dólar (08/10/2026)

- [x] Fonte principal Investing para referências de soja, milho e trigo em US$/bushel e USD/BRL em R$/US$; horário original e identificação de dados derivados.
- [x] Consulta automática em tela visível a cada 60 segundos, cache limitado, falhas com preservação e controle de consultas, acesso por permissão de consulta.
- [x] 58 testes de mercado/relatórios e sete testes finais de integração aprovados; frontend/TypeScript/build final aprovados, consulta real dos quatro instrumentos validada e backup verificado. Sem migration adicional.
- [ ] Conferência visual autenticada: navegador com sessão expirada.

Evidências e limitações: docs/decisoes/2026-10-08-investing-dolar.md.

### Incremento — integrações sem serviços pagos (10/10/2026)

- [x] IA generativa local de leitura, isolada da internet, com contexto permitido e evidência oficial; resposta real conferida.
- [x] Satélite e NDVI regional NASA/MODIS com data do catálogo e legenda oficiais, sem média fictícia por talhão.
- [x] Entradas, saídas e saldos financeiros no Resumo Executivo, respeitando permissões e filtros, sem tratar caixa como lucro.
- [x] 28 testes PostgreSQL isolado, frontend/test/TypeScript/build, Django/migrations e diff aprovados; backups verificados e aplicativo local atualizado.
- [ ] Radar com fonte gratuita autorizada para ERP, rentabilidade com base suficiente e média NDVI por talhão. Não declarar essas ampliações implementadas.

Evidências, limites e carregamento inicial da IA: docs/decisoes/2026-10-10-integracoes-sem-custos.md. Sem commit, push ou merge.

### Incremento — abas da versão web (10/10/2026)

- [x] Contadores em Cargas/Vendas/Financeiro, abrangência explícita de filtros e totais, paginação parcial identificada e rolagem móvel das abas.
- [x] Preservação de filtros/formulários, proteção de saída no Financeiro e respostas antigas de Vendas descartadas.
- [x] 54 testes financeiros PostgreSQL isolado, frontend/TypeScript/Vite, Django/migrations e revisão de diff aprovados; conferência autenticada e móvel, frontend 5174 atualizado.

Evidências, arquivos, backups e limites: docs/decisoes/2026-10-10-abas-web.md. Sem migrations, alterações operacionais ou operações Git.

### Incremento — melhorias após auditoria de romaneios web (10/10/2026)

- [x] Consultas paginadas no banco para romaneios de entrada/saída, contagem e peso ativo de todos os resultados filtrados, sem mudar os endpoints dos demais fluxos.
- [x] Atualização conjunta de entradas próprias/terceiros; carregamento, falha, período inválido e resultado vazio separados; filtros ativos e horário da consulta.
- [x] Abas ocultas sem consultas, cancelamento e descarte de respostas antigas, filtros preservados e documentos existentes reutilizados.
- [x] Sete novos testes PostgreSQL, frontend/TypeScript/Vite, Django/migrations e conferência autenticada/móvel aprovados. Suíte ampliada de 347 casos com cinco skips e dois erros de fixtures antigas; corrigidos os dois testes de migrations e reteste aprovado, sem mudança de modelos/migrations.
- [x] Backup verificado, frontend local 5174 saudável e revisão do diff concluída. Sem dados operacionais alterados, commit, push, merge ou produção.

Evidências, arquivos, comandos e limites: docs/decisoes/2026-10-10-auditoria-romaneios-web.md.

### Incremento — comissão percentual de Transportes (12/10/2026)

- [x] Comissão manual em %, cálculo sobre receitas menos AREIA/PEDRA, base negativa zerada.
- [x] Prévia sem gravação, tabela com percentual/base/valor, relatórios e CSV recalculados.
- [x] Nove percentuais recuperados da planilha, valores históricos preservados, migrations aditivas.
- [x] 19 testes de Transportes em PostgreSQL isolado, frontend/TypeScript/Vite e Django aprovados.

Evidências e backups: docs/decisoes/2026-10-12-transportes.md. Sem operações Git ou produção.

### Incremento — telas de Transportes por motorista ou placa (12/10/2026)

- [x] Formulários com rolagem livre, inserção separada da consulta de dados.
- [x] Consulta de remunerações com filtros e agrupamento por motorista ou placa.
- [x] Frontend/TypeScript/Vite aprovados, backup verificado; sem migrations.

Evidências: docs/decisoes/2026-10-12-transportes.md.

### Incremento — impressão de Transportes (12/10/2026)

- [x] Fonte 11pt nas tabelas, A4 paisagem e proteção contra quebra de datas/valores.
- [x] Frontend/TypeScript/Vite e diff aprovados; impressão física não verificada.

Evidências: docs/decisoes/2026-10-12-transportes.md.

### Incremento — compactar impressão de Transportes (12/10/2026)

- [x] Menor espaçamento/entrelinha, coluna do motorista ampliada e fonte 10,5pt.
- [x] Testes frontend, TypeScript/Vite e revisão de diff aprovados.

Evidências e limites: docs/decisoes/2026-10-12-transportes.md.


## Incremento — melhorias da auditoria geral (13/10/2026)

- [x] Dezesseis entregas técnicas implementadas e validadas nos limites documentados.
- [x] 762 casos gerais (seis skips), 103 pertinentes finais (um skip), frontend/TypeScript/Vite e migrations aprovados.
- [x] Migration transportes.0004 aplicada após backup; acessos e regra de mínimo preservados.
- [ ] HTTPS/CSP efetiva, cobertura de auditoria em operações em lote e demais ampliações explicitadas.

Evidências, backups, arquivos e sincronização: docs/MELHORIAS-AUDITORIA-20261013.md.
Sem merge nem produção.


## Incremento — holerite mensal por motorista (13/10/2026)

- [x] Seleção de mês e motorista, prévia A4, salário/comissão/total e assinatura.
- [x] Histórico e todas as placas preservados; acesso de impressão validado no backend.
- [x] Testes pertinentes, frontend/TypeScript/Vite, check/migrations e atualização local aprovados.

Evidências, backups e limites: docs/decisoes/2026-10-13-holerite-motoristas.md.
Sem migration nem alteração de dados operacionais.


## Incremento — fretes de cargas e vendas por mês/placa (13/10/2026)

- [x] Cruzamento das origens ativas, frete/comissão manuais e decisão explícita para evitar repetição.
- [x] Associação à remuneração mensal, holerite e relatórios com comissão manual separada.
- [x] Reenvio, edição obsoleta, cancelamento, vínculos e permissões protegidos; testes pertinentes estabilizados.
- [x] Migration transportes.0005 aditiva aplicada após backup; interface 5174 saudável.

Evidências, resultados e limites: docs/decisoes/2026-10-13-fretes-cargas-vendas.md.
Nenhum dado de frete/comissão preenchido automaticamente. Sem commit/push/merge.


## Incremento — ranking financeiro e eficiência de motoristas (13/10/2026)

- [x] Rankings separados por resultado e margem, com salário/comissão/custos registrados.
- [x] Indicador de carga média documentada, motorista histórico e conferências manuais, sem origens canceladas.
- [x] Filtros, pendências de cadastro, critérios, impressão e CSV preservados; permissões respeitadas.
- [x] 61 casos PostgreSQL (um skip), frontend/TypeScript/Vite, Django/migrations e atualização local aprovados.

Evidências e limites: docs/decisoes/2026-10-13-ranking-motoristas.md.
Sem migration nova nem alteração de registros operacionais; sem commit/push/merge.

## Incremento — controle de cavaco (15/10/2026)

- [x] Cadastro/edição de cargas, pagamento, filtros e cálculo de líquido e total.
- [x] Módulo e permissões por ação, auditoria e migration aditiva estoque.0009 aplicada.
- [x] Romaneio de cada carga com duas vias em uma única página A4 e assinaturas.
- [x] Dez testes PostgreSQL isolado, regressões de estoque/autenticação, testes frontend e build Docker aprovados.
- [x] Tela desktop/celular e cadastro com API simulada conferidos; PDF de uma página verificado.

Evidências, backups e limites: [controle de cavaco](decisoes/2026-10-15-cavaco.md).
Sem importação histórica automática, commit, push, merge ou produção.

Importação histórica posteriormente autorizada: 31 cargas de CAVACO.xlsx
incorporadas, 819.250 kg e R$ 278.175,45; totais/pagamentos, ausência de
reimportação duplicada e 31 romaneios conferidos pela API. Backup completo
com restauração isolada aprovado; origem por linha registrada no histórico.
Uma carga sem motorista foi identificada explicitamente como ausente na fonte.
Demais cargas existentes preservadas. Detalhes na decisão de cavaco acima.

## Incremento — edição/exclusão e Financeiro de cavaco/diesel (15/10/2026)

- [x] Exclusão lógica confirmada, permissões, auditoria e preservação dos históricos.
- [x] Diesel com vencimento automático no próximo dia útil quando necessário, feriados nacionais e sem média ponderada.
- [x] Uma conta a pagar por origem: 32 de cavaco e duas de diesel, todas pendentes para baixa posterior, conforme autorização.
- [x] Edição sincroniza títulos pendentes; liquidados protegidos; reexecução sem duplicação.
- [x] 52 testes PostgreSQL, frontend/TypeScript/build, verificação da API e fluxos visuais simulados aprovados.

Evidências, regras e backups: [cavaco/diesel no Financeiro](decisoes/2026-10-15-cavaco-diesel-financeiro.md).
Sem exclusão física, baixa automática, commit, push, merge ou produção.

## Alteração solicitada — retirada de Clima e Mercado (15/10/2026)

- [x] Removidos da navegação, permissões ativas, painel e relatórios.
- [x] Rotas públicas desativadas e alertas climáticos retirados do assistente.
- [x] Dados e migrations preservados; sem alteração estrutural do banco.
- [x] Testes pertinentes, frontend/TypeScript/build, conferência visual e HTTP aprovados.

Backup e evidências: [retirada dos módulos](decisoes/2026-10-15-retirar-clima-mercado.md).
Aplicação local na porta 5174; sem commit, push, merge ou produção.


## Incremento — compras, estornos e consulta financeira (16/10/2026)

- [x] Compras com conta a pagar; estorno desconta quantidade e valor; compra paga gera crédito de fornecedor.
- [x] ANKOR conferida: 2.000 L e R$ 100.000,00 líquidos, título #41; originais e estorno preservados.
- [x] Financeiro compacto, sem ajuda/favoritos; 72 testes PostgreSQL, frontend/TypeScript/build e API aprovados; ativo localmente.
- [ ] Conferência visual autenticada no navegador.

Evidências e limites: [compras e estornos](decisoes/2026-10-16-compras-estornos-financeiro.md).


## Incremento — área realizada e revisão geral de telas (16/10/2026)

- [x] Área realizada opcional em Operações e relatórios, sem inferência histórica; correção versionada e conclusão atômica. Migration producao.0002 aplicada; 72 testes PostgreSQL aprovados.
- [x] Fontes e espaçamentos de tela padronizados; compras com originais separados e ações recolhíveis; extravasamento de diesel e carregamento residual de Transportes corrigidos.
- [x] Navegação autenticada pelos 21 módulos e 33 abas em desktop/celular; testes frontend, TypeScript/Vite, Django/migrations e revisão de diff aprovados; atualização local. Limites da conferência documentados.
- [x] Empréstimos de motoristas, juros, pagamentos no holerite e calculadora de prestações: concluídos no incremento abaixo após validação.

Evidências: [layout e fontes](decisoes/2026-10-16-revisao-layout-fontes.md) e [área realizada](decisoes/2026-10-16-area-realizada-operacoes.md).

## Incremento — empréstimos e cálculo de prestações (16/10/2026)

- [x] Empréstimos por motorista, juros únicos opcionais, pagamentos datados, saldo e histórico/estorno com justificativa; idempotência, concorrência e permissões.
- [x] Empréstimo pago identificado no holerite, bruto/líquido separados e conta a pagar sincronizada, protegendo títulos liquidados e vínculos históricos.
- [x] Simulador SAC no Financeiro baseado na planilha, juros anuais/dias reais, periodicidade e carência explícita; sem lançamento automático.
- [x] 139 testes PostgreSQL aprovados (1 referência privada antiga indisponível), frontend/TypeScript/build, migrations, revisão de diff e conferência autenticada desktop/celular. Atualização local na porta 5174.

Critérios, backups, evidências e limites: [empréstimos e prestações](decisoes/2026-10-16-emprestimos-prestacoes.md).

## Incremento — aba e impressão do cálculo de prestações (16/10/2026)

- [x] Aba própria no Financeiro, preservando lançamentos e a simulação ao alternar.
- [x] Prévia exclusiva e impressão/PDF pelo navegador com parâmetros, critérios, totais e parcelas; permissão de impressão respeitada.
- [x] Testes frontend, TypeScript/Vite, conferência autenticada desktop, dimensões móveis e revisão do diff aprovados; frontend local atualizado. Impressão física/PDF nativo não executados.

Evidências, backups e limites: [aba e impressão de prestações](decisoes/2026-10-16-aba-prestacoes-impressao.md).

## Incremento — faturamento em A4 retrato e Arial 12 (19/10/2026)

- [x] Impressão e PDF em retrato, Arial 12; Excel com aba de impressão própria e dados preservados.
- [x] Testes de faturamento, PDF/Excel, frontend e build aprovados; PDF conferido visualmente e aplicação local atualizada.

Evidências, backup e configuração das fontes: [faturamento A4 Arial 12](decisoes/2026-10-19-faturamento-a4-arial12.md).

- [x] Revisão do faturamento: propriedades em linhas de tabela na impressão/PDF/Excel, mantendo A4 retrato e Arial 12; testes e conferência visual do PDF aprovados.

- [x] Faturamento: produto antes dos totais em destaque, cabeçalho compacto e coordenadas na mesma linha; PDF/Excel e frontend validados.

- [x] Faturamento: cabeçalho resumido em duas linhas (produto/totais e dados complementares), validado em PDF, Excel e frontend.

- [x] Faturamento: mais largura para propriedade/produtor e descrição completa de embalagens (ex.: 7 BALDES DE 20 LITROS), com testes e conferência visual.

- [x] Propriedades: clicar no nome abre o mapa logo abaixo do cadastro, com suporte a GMS e decimais e aviso para coordenadas ausentes; testes frontend aprovados. [Detalhes](decisoes/2026-10-19-mapa-propriedade-selecionada.md).

- [x] Mapa da propriedade: segundo clique no cartão também recolhe o mapa, preservando os cliques nas ações e dentro do mapa.

- [x] Grupos de colheita: Cultura e Safra no cadastro, edição e lista; migration aplicada, dez testes de grupos/histórico e frontend/build aprovados. [Detalhes](decisoes/2026-10-19-grupos-cultura-safra.md).

- [x] Propriedades: arquivamento reversível autorizado, filtro/restauração, exclusão protegida com vínculos reais e auditoria; migration, treze testes e frontend/build aprovados. [Detalhes](decisoes/2026-10-19-arquivamento-propriedades.md).

- [x] Grupos de colheita: nomes dos excluídos liberados para novo cadastro, preservando histórico e unicidade dos não excluídos; migration aplicada e onze testes aprovados. [Detalhes](decisoes/2026-10-19-grupos-nomes-excluidos.md).

- [x] Propriedades: edição do CAD/PRO substitui o vínculo atual sem apagar históricos; Electra corrigida pontualmente e 23 testes aprovados. [Detalhes](decisoes/2026-10-19-substituicao-cadpro-propriedade.md).

- [x] CAD/PRO atual: revisão dos cadastros legados concluída, mantendo o último salvo no Sítio Bom Jesus; zero propriedades com vínculos ativos duplicados, históricos preservados.
