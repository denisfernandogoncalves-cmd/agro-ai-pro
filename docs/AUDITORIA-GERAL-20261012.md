# Auditoria geral — 12/10/2026

> Registro histórico da auditoria inicial. Implementações, retificações e
> resultados posteriores: [melhorias de 13/10](MELHORIAS-AUDITORIA-20261013.md).

## Resultado e alcance

A principal pendência é a divergência entre o código sincronizado e o aplicativo
em uso. O container `agro-ai-pro-backend-1` monta
`.worktrees/runtime-origin-main` em `/app`; essa árvore contém alterações
rastreadas e arquivos novos não enviados no checkpoint `75e1cfd` da branch
`codex/modernizacao-visual`. A sincronização anterior contemplou somente a árvore
principal. Não integrar essas árvores automaticamente: possuem diferenças de
models, migrations, permissões, contratos e interface.

Revisão técnica transversal de configurações, autenticação, permissões,
propriedades/KML, talhões, CAD/PRO, grãos/cargas/transferências, vendas/contratos,
financeiro, estoque/faturamento, operações, máquinas, transportes, importações,
relatórios, clima, mercado, assistente, interface, offline, instalador e CI.
Profundidade maior nos componentes compartilhados e nos achados abaixo.
Não é certificação de todos os fluxos, pentest, auditoria contábil ou teste de carga.
Nenhum dado operacional ou código funcional foi alterado.

## Melhorias prioritárias

P1 = alta prioridade; P2 = média prioridade. As propostas não foram implementadas.
As evidências são relativas à árvore ativa, salvo indicação da árvore principal.

| # | Prioridade | Evidência / problema | Melhoria e critério de aceite |
|---|---|---|---|
| 1 | P1 | Runtime diferente da branch sincronizada, com muitas alterações não commitadas. | Consolidar a versão operacional em uma branch revisável, preservando ambas as árvores; instalação limpa deve reproduzir o programa em uso e suas migrations. |
| 2 | P1 | Árvore principal: CAD/PRO e vendas ausentes de `INSTALLED_APPS`; migration de grãos depende de `cadpro.0001_initial`; módulo offline importa componentes ausentes. | Resolver as dependências e rotas ao consolidar a versão; exigir migrations, testes e build aprovados antes de integrar o checkpoint. |
| 3 | P1 | `check --deploy` ativo: seis alertas, incluindo DEBUG, força da chave, HTTPS e cookies; Compose usa `runserver`. | Criar perfil de implantação seguro com servidor apropriado, chave obrigatória e TLS/cookies; validar separadamente do desenvolvimento e preservar acesso local durante a transição. |
| 4 | P1 | PostgreSQL ativo publica `0.0.0.0:5432`, apesar de o Compose do runtime declarar loopback. | Conciliar configuração efetiva com o Compose; restringir banco a loopback/rede interna ou clientes explicitamente autorizados. Verificar novamente as portas após aplicação planejada. |
| 5 | P1 | `accounts/views.py` e settings não definem throttling de login/refresh; Nginx não possui limite específico. | Limitar tentativas por origem/conta, registrar falhas sem credenciais e testar resposta 429 e recuperação, sem bloquear usuários legítimos indevidamente. |
| 6 | P1 | `accounts/access.py`: usuário sem configuração de acesso recebe todos os módulos; permissões omitidas recebem todas as ações; staff tem bypass. | Definir política explícita de provisionamento com o PO e oferecer perfil mínimo; testar usuário novo, staff e permissões incompletas. É mudança de política, não aplicar automaticamente. |
| 7 | P1 | `core/auditoria.py`: lista APPS não inclui `transportes` nem `importacoes`; requer contexto de requisição; operações em lote podem não emitir signals. | Cobrir alterações de transportes/importações e execuções por scripts com ator/origem/antes/depois; testar importação, edição, exclusão e transação revertida sem registrar secrets. |
| 8 | P1 | Testes frontend do runtime falham por `@tailwindcss/vite` ausente no node_modules local. | Reproduzir dependências com instalação pelo lockfile em ambiente isolado; exigir que instalação limpa, testes e build funcionem sem depender do estado do computador. |
| 9 | P2 | `estoque/services.py`: compara cada lote com o mínimo do produto e conta lotes em `itens_abaixo_minimo`. | Definir com o PO se o mínimo é por produto/local/propriedade; somar na dimensão definida e contar itens distintos. Testar produto dividido entre dois lotes cujo total supera o mínimo. |
| 10 | P2 | `relatorios/selectors.py`: `_pagina` usa len de coleção materializada; `_financeiro` gera lista completa; grãos materializa várias coleções. | Paginar no banco e separar totais da página; testar resultados equivalentes e medir tempo/memória com histórico grande. Exportações completas precisam de estratégia própria. |
| 11 | P2 | Sem paginação global em REST_FRAMEWORK; vários ViewSets financeiros, de estoque e máquinas retornam listas completas. | Introduzir paginação com limites e adaptar os consumidores em conjunto; comprovar que seletores, totais e exportações não perdem registros. |
| 12 | P2 | `core/edicao_concorrente.py` só compara versão quando ela é enviada; máquinas, operações e transportes ainda usam edição comum. | Tornar versão obrigatória nas edições críticas e expandir controle de concorrência; segunda gravação obsoleta deve retornar 409 preservando o rascunho. |
| 13 | P2 | `clima/views.py` passa datas de query diretamente ao ORM; outros filtros numéricos também variam entre módulos. | Validar filtros com serializers/utilitários compartilhados; datas inválidas, IDs não numéricos e intervalos invertidos devem retornar 400 consistente, sem erro interno. |
| 14 | P2 | Tokens access/refresh ficam em localStorage (`auth/sessionCoordinator.ts`); Nginx não configura CSP. | Avaliar refresh em cookie HttpOnly e CSP, considerando CSRF, rede local e instalador. Validar logout, abas simultâneas, renovação e funcionamento offline após qualquer mudança. Não foi demonstrada exploração XSS. |
| 15 | P2 | `config/urls.py`: health retorna apenas status fixo; container saudável não comprova consulta ao banco nem adequação de implantação. | Separar liveness de readiness; readiness deve verificar dependências essenciais com timeout curto e retornar indisponível quando necessário, sem expor dados internos. |
| 16 | P2 | CI e npm test não incluem todos os scripts dedicados; resultados antigos não validam o conjunto atual. | Inventariar testes por módulo e executar casos de coordenadas, romaneios e offline nas etapas correspondentes; falhar se a descoberta backend for vazia. Incluir fluxo real de compra/consumo/venda/estorno. |
| 17 | P2 | `transportes/models.py` tem mínimos e limites em validators, sem constraints equivalentes para quantidade/valores/percentuais. | Acrescentar constraints após conferir dados existentes; testar escrita via API, importação e escrita direta em banco isolado. Não corrigir registros automaticamente. |
| 18 | P2 | Clima, mercado e IA dependem de dados externos e atualizações; chamadas de atualização são síncronas e já possuem timeout. | Mostrar idade do dado, última tentativa e falha, distinguindo dado preservado de atualização bem-sucedida; deduplicar atualizações concorrentes e medir latência antes de adotar processamento em segundo plano. |

## Evoluções funcionais para a próxima etapa

Estas são propostas de produto, não defeitos confirmados nem afirmações de ausência
total do recurso. Complementam funções já existentes:

- Financeiro: projeção semanal de caixa com parcelas, vencimentos, situação e
  base monetária identificadas; previsão não deve ser apresentada como saldo bancário.
- Insumos: custo realizado por talhão/safra com rastreabilidade até o consumo;
  sugestão de lote por validade com confirmação explícita e unidades compatíveis.
- Máquinas: manutenção por horas restantes e custo/hora discriminando combustível,
  manutenção e demais custos disponíveis; campos ausentes devem ficar explícitos.
- Grãos/vendas: investigação de diferenças de saldo com documentos de origem,
  reservas, entregas e estornos; sem ajuste automático de estoque.
- Propriedades/talhões: conferência de área declarada, área KML e soma vinculada,
  com origem e tolerância informadas; sem alterar cadastros pela comparação.
- Interface: ensaio completo de teclado/celular dos fluxos críticos, incluindo
  rascunhos, edição concorrente, mensagens de erro e impressão de romaneios.

## Pontos existentes a preservar

Transações e bloqueios em grãos, vendas e estoque; proteção de vínculos; preview
e confirmação de importações; limits de ZIP; isolamento de sessão no logout;
conversões GMS explícitas; histórico de contratos; fontes e unidades de mercado;
IA local isolada; scripts de backup privado e teste em PostgreSQL exclusivo.

A leitura atual confirmou correções que constavam na auditoria de 07/10:
validação decimal centralizada, tratamento de 29/02, limite Nginx de importações
de 11m para arquivos de até 10 MB, inativação de contrato com versão e motivo,
runner de testes com rótulo padrão apps. Não repetidas como falhas atuais.

## Verificações desta auditoria

- Branch principal limpa ao início; nenhuma alteração funcional realizada.
- Docker: backend/frontend/PostgreSQL/Redis saudáveis; IA local em execução.
- Mount do backend confirmado: `.worktrees/runtime-origin-main`.
- Backend ativo `manage.py check`: aprovado.
- Backend ativo `makemigrations --check --dry-run`: nenhuma mudança detectada.
- Backend ativo `check --deploy`: seis alertas; executado no perfil ativo de
  desenvolvimento, não em uma implantação HTTPS certificada.
- Frontend ativo `npm test`: bloqueado antes dos testes por dependência ausente.
- Frontend ativo `test-coordenadas.mjs`: mesmo bloqueio de Vite.
- Frontend ativo `test-romaneios.mjs`: aprovado.
- `python scripts/test_backend_isolado.py apps.transportes apps.financeiro
  apps.maquinas apps.core.test_valores`: 83 testes aprovados em PostgreSQL
  exclusivo, em 15,371 s. A base temporária foi removida pelo runner ao finalizar.
  Nenhuma chamada inválida foi feita contra registros reais. Openpyxl avisou
  que uma extensão de validação de planilha não é suportada; não causou falhas.
- Resultados da árvore principal de minutos antes: check aprovado; migrations
  e testes bloqueados pela dependência CAD/PRO; build bloqueado por imports
  ausentes e acesso a tsbuildinfo; componentes/auth/shell/GMS/offline aprovados.

Sem suíte geral nova, teste de carga, pentest, ensaio de restauração nesta rodada,
consulta externa de vulnerabilidades ou validação manual de todas as telas.
Os testes da auditoria de 07/10 são históricos e não são aprovação do código atual.

## Preservação

Backups novos antes de registrar o relatório:

- principal: `backups/visual-20261012-224729-640048`;
- runtime: `.worktrees/runtime-origin-main/backups/agro-ai-pro-2026-10-12-224735-012575`.

Código local, banco e uploads preservados, ZIP/dump verificados e hashes SHA-256
registrados nos manifestos privados. Não houve restauração, migration aplicada,
commit, push, merge ou publicação nesta auditoria.
