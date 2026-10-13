# Modernização visual — entrega inicial, 07/10/2026

## Etapa 1 — identidade agrícola e navegação, 12/10/2026

Pedido atual: modernização por etapas. A branch específica existente
`codex/modernizacao-visual` foi reutilizada, preservando alterações locais de
outras tarefas. Esta entrega evolui a prévia deste checkout; não substitui
o checkout operacional `runtime-origin-main` nem o serviço na porta 5174.

Análise: React/TypeScript/Vite, navegação por estado em `App.tsx`, CSS próprio,
ícones SVG, mapa Leaflet e gráfico SVG existentes. Shell/dashboard já estavam
integrados e foram reutilizados. APIs, autenticação, permissões, filtros dos
módulos, cálculos de estoque/CAD/PRO e bloqueios comerciais não foram alterados.
Sem dependências adicionais, alterações de backend ou migrations.

Plano e critérios de aceite:

1. Etapa 1: identidade verde profundo/verde agrícola/cinza/dourado, menu
   categorizado com busca, recolhimento desktop e fechamento móvel; dashboard
   com fontes existentes, atalhos, estados de consulta e gráfico interativo.
   Preservar acesso aos 15 módulos e logout, temas claro/escuro, foco visível,
   layouts adaptáveis e preferência de movimento reduzido. Validar testes,
   TypeScript e build; registrar limitações sem afirmar homologação completa.
2. Etapa 2: padronizar internamente tabelas, filtros, formulários, cabeçalhos
   e mensagens dos módulos, com testes/build por etapa e preservação funcional.
3. Etapa 3: homologar navegação operacional, contraste e responsividade com
   sessão autenticada e dados reais, revisar desempenho e acessibilidade.

Implementado nesta etapa: menu em quatro categorias com pesquisa insensível
a acentos; estado sem resultados; limpar busca ao navegar/recolher; atalhos
para cargas, CAD/PRO, vendas e relatórios; painel de boas-vindas; tokens de
superfície, bordas e texto; cores de mensagens em tema escuro; tabelas do
dashboard com cabeçalho fixo e números alinhados. Gráfico existente ganhou
pontos consultáveis por ponteiro, toque e foco de teclado, com data, valor e
unidade reais. Mapa aceita centro com coordenada zero. Nenhuma métrica fictícia.

Arquivos desta revisão: `frontend/src/components/AppShell.tsx`,
`frontend/src/pages/Dashboard/DashboardPage.tsx`, `frontend/src/styles.css`,
`frontend/src/pages/Mercado/GraficoMercado.tsx`,
`frontend/scripts/test-shell.mjs` e este documento. Alterações anteriores em
App, API, autenticação e backend foram preservadas e não pertencem a esta revisão.

Backup privado: `backups/visual-20261012-210754-978695/`. Código rastreado e
não rastreado, uploads e patch; dump PostgreSQL customizado. ZIP/CRC e catálogo
do dump verificados, tamanhos e SHA-256 em `manifesto.json`. Não houve restauração.

Validação:

- `npm test`: 15 testes de componentes/geometria/PWA e 13 cenários de
  autenticação aprovados. No sandbox o socket local falhou com EACCES; execução
  autorizada fora do sandbox aprovada.
- `node scripts/test-shell.mjs`: acesso aos 15 módulos, categorias, logout,
  temas claro/escuro, pontos acessíveis do gráfico e histórico vazio aprovados.
  Valores usados nesse teste são fixtures, não aparecem na aplicação.
- `npm run build`: bloqueado por cache `tsconfig.tsbuildinfo` com acesso negado
  e imports preexistentes ausentes em `src/offline/TrabalhoOffline.tsx`
  (`components/AcoesContext`, `api/usuarios`). Código offline desconectado desta
  prévia foi preservado; não foram criadas permissões artificiais para compilá-lo.
- TypeScript da interface conectada: `npx tsc -p
  ../backups/visual-20261012-210754-978695/tsconfig.visual.json --noEmit`, aprovado.
  Configuração temporária exclui apenas a pasta offline e desativa cache;
  não substitui o build completo pendente.
- `npx vite --configLoader runner build --outDir
  ../backups/visual-20261012-210754-978695/dist-visual`: aprovado, artefatos privados.
  Bundle aproximadamente 531 kB (152 kB gzip), aviso acima de 500 kB permanece.
- Não existe script lint. Backend/migrations sem alterações nesta revisão.

Pendências reais: build completo depende da tarefa offline e da permissão de
cache; homologação visual autenticada em desktop/celular e interações no
navegador; padronização interna dos módulos nas próximas etapas. Nenhum status
de Sprint foi marcado como concluído. Sem commit, push, merge ou publicação.

## Revisão solicitada em 09/10/2026

Escopo desta tarefa: aproveitar a prévia existente na branch
`codex/modernizacao-visual`, sem substituir o checkout operacional.
Auditoria: React/TypeScript/Vite, CSS próprio e componentes reutilizáveis;
sem Tailwind/Lucide nas dependências. Módulos do menu possuem páginas reais.
O contexto JWT fornece estado de sessão, sem nome ou catálogo de permissões
por módulo. Não foram inventados configurações, notificações ou permissões.

Plano executado: identidade azul-marinho/verde; menu recolhível no desktop;
tema claro/escuro com preferência local; fechamento móvel com Escape;
dashboard com saldos físico, comprometido e disponível da API existente,
mais horário da consulta e identificação de resultado parcial.
O horário indica a consulta, não a atualização na origem.
Filtro de safra e seletor de propriedade existentes foram preservados.
Ícones SVG existentes foram reutilizados; adoção de Lucide fica pendente.
Componentes aprimorados: `AppShell` e `DashboardPage`; nenhum novo componente.
Arquivos alterados nesta revisão: os dois componentes, `styles.css` e este documento.

Backup: `backups/visual-20261009-085609/`, código local incluindo alterações
pendentes, uploads e dump PostgreSQL. ZIP e catálogo do dump verificados;
hashes SHA-256 registrados no manifesto. Nenhuma mutação de dados ou migration.

Validação em container temporário Node 22: `npm test` aprovado (15 testes de
componentes/geometria/PWA e 13 cenários de autenticação); build Vite aprovado,
com aviso de bundle de 524 kB. `npm run build` local não aprovado: cache
TypeScript sem permissão e imports preexistentes ausentes em
`src/offline/TrabalhoOffline.tsx` (`AcoesContext` e `api/usuarios`).
Esse módulo não é importado pelo aplicativo desta prévia. A checagem completa
TypeScript permanece pendente até resolver a tarefa offline correspondente.
Não existe script lint. `git diff --check` aprovado.
Checagem TypeScript do frontend conectado à prévia aprovada com configuração
temporária no diretório de backup, excluindo somente o diretório offline
preexistente e desconectado. Isso não substitui a checagem completa pendente.

Homologação visual autenticada, móvel e de contraste nos demais módulos ainda
pendente. Backend, regras comerciais, rotas, autenticação e dados preservados.
Próxima etapa: homologar este shell/dashboard antes de padronizar módulos.
Sem commit, push, merge ou implantação.

**Prévia preservada da pasta principal, não implantada em 5174.** O endereço
indicado depois pelo Product Owner roda o checkout `runtime-origin-main`.
A entrega efetivamente disponibilizada nele está documentada em
`.worktrees/runtime-origin-main/docs/decisoes/2026-10-07-modernizacao-visual.md`.
Não substituir a versão operacional por este protótipo, pois o checkout
runtime possui módulos e controles mais recentes.

Branch: `codex/modernizacao-visual`. Fase 1 implementada e prévia funcional
da Fase 2 disponível para homologação. A padronização interna dos demais
módulos aguarda aprovação visual do Product Owner, conforme o pedido.

## Escopo e critérios

Menu lateral verde escuro com todos os módulos existentes e acesso aos módulos
de cargas, grupos de colheita, vendas e saldos. Dashboard inicial após login,
menu recolhível, indicação de conexão, logout e seletor de propriedade.
Estilos novos limitados ao shell/dashboard; formulários e regras existentes
preservados. Sem novas dependências, alterações de backend ou migrations.

Arquivos: `frontend/src/App.tsx`, `frontend/src/styles.css`,
`frontend/src/components/AppShell.tsx`,
`frontend/src/pages/Dashboard/DashboardPage.tsx` e
`frontend/scripts/test-auth.mjs` (teste ajustado à nova árvore privada).

## Fontes reais e filtros

- Área: `listarTalhoes`, por propriedade e safra, percorrendo todas as páginas;
  soma da área declarada por cultura atual, sem percentuais fictícios.
- Estoque: `consultarPainelSaldos`, por propriedade/safra, em kg;
  tabela preserva cada posição de CAD/PRO, cultura, safra, classificação e armazém.
- Mercado: `carregarPainelMercado`; valores, unidades, datas e avisos da API;
  gráfico existente por produto. Não representa preço local da propriedade.
- Clima: `listarPrevisoes`, por propriedade; somente previsões vigentes/futuras,
  temperatura máxima identificada como prevista, sem temperatura atual fictícia.
- Mapa: componente `MapaTalhao` existente, primeiro talhão com geometria e centro;
  usa OpenStreetMap, sem satélite ou NDVI fictício.
- Assistente/alertas: `obterInsights`, por propriedade. Análise independente
  do filtro de safra, identificada no painel. Nenhuma chamada de atualização
  externa nem mutação de dados é disparada pelo dashboard.

Consultas independentes usam `Promise.allSettled`; uma falha não esconde as
outras fontes. Respostas de seleções anteriores são descartadas. Estados sem
dados ou integração mostram indisponibilidade, sem inventar números.
O seletor superior aplica-se ao dashboard; cada módulo mantém seus filtros.

## Segurança e backup

Backup privado ignorado pelo Git:
`backups/visual-20261007-220502/`. Código atual, incluindo arquivo não rastreado
preexistente `docs/INCIDENTE-LOCAL-20261001.md`, uploads, patch e dump PostgreSQL.
ZIP verificado, catálogo do dump validado por `pg_restore --list`, SHA-256 de
arquivos e artefatos em `manifesto.json`. Nenhuma restauração ou alteração de
dados. Nenhum commit, push ou merge.

## Validações e homologação pendente

TypeScript: `npx tsc --noEmit --incremental false` aprovado.
Build e testes executados em cópia isolada com `node:22-alpine`,
`npm ci --no-audit --no-fund`, `npm run build` e `npm test`.
Build aprovado; aviso de bundle JavaScript acima de 500 kB.
15 testes de componentes/geometria/PWA e 13 cenários de autenticação/logout.
O cache TypeScript local apresentou acesso negado; testes SSR no Node 24 local
apresentaram incompatibilidade de resolução CommonJS. A validação isolada
usa a versão Node 22 definida no Dockerfile sem alterar dependências locais.
Não existe script de lint neste frontend. `git diff --check` aprovado.

Prévia: `npm run dev -- --host 127.0.0.1 --port 5173 --strictPort`,
acessível em `http://127.0.0.1:5173/`, usando a API existente na porta 8000.
Tela de login verificada no navegador. Dashboard autenticado, fidelidade visual,
responsividade, navegação operacional e filtros com dados reais ainda exigem
homologação no navegador; sem credenciais fornecidas nem sessão ativa de revisão.

Limitações da prévia: saudação genérica (contexto de autenticação não fornece
nome), indicador agregado de vendas indisponível com acesso funcional ao módulo,
mapa de um talhão, gráfico de uma cultura por vez, ausência de pesquisa global.
A Fase 2 completa e a Fase 3 permanecem pendentes. Não alterar status das Sprints
já concluídas por causa desta entrega visual parcial.
