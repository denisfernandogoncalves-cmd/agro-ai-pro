# Impressão A4 de Propriedades — 21/09/2026

## Escopo e referência

A aba Propriedades ganhou uma composição exclusiva de impressão, mantendo o formulário, a lista, a busca e o mapa da tela. A revisão solicitada no mesmo dia substituiu a referência inicial por `backups/referencias-layout-20260921-1802/propriedades-referencia-estoque.png` (SHA-256 `AE1A61C0FA2FAB3E2DBEF8E1FE13E2A2FE28E6DCFD49C530505427FFA8C7465B`). A página A4 paisagem agora segue o visual da impressão de Compras de estoque: título simples alinhado à esquerda, fundo branco, cabeçalho de tabela claro e apenas separadores horizontais. A faixa de contexto e as bordas verticais da versão inicial foram removidas.

O relatório imprime as propriedades da consulta carregada, com CAD/PRO, proprietário, município/UF e áreas declarada e calculada em alqueires paulistas. O total declarado soma todas as linhas. O total calculado só é exibido quando todas as propriedades têm essa medida; caso contrário, aparece um traço e uma nota explicativa. Nenhum dado foi modificado.

## Preservação e validação

- Checkout inicial: `.worktrees/runtime-origin-main`, branch `codex/layout-global-20260921`, commit `fb3362918967a29a243c603df706e4ebaa6da2bf`, árvore limpa. A execução foi isolada na branch local `codex/propriedades-impressao-a4-20260921`.
- Backup validado antes das edições: `D:/PROJETOS/AGRO-AI-PRO/backups/agro-ai-pro-2026-09-21-174350-797240`, contendo ZIP de código, dump PostgreSQL, ZIP de uploads, patch e estado Git. O manifesto registra SHA-256, CRC dos ZIPs e leitura integral do dump.
- Antes da revisão visual, outro backup validado preservou inclusive as alterações ainda não commitadas: `D:/PROJETOS/AGRO-AI-PRO/backups/agro-ai-pro-2026-09-21-180246-441967`. Seu ZIP de código inclui o componente e este documento; o manifesto registra hashes e a validação do banco e dos uploads.
- `npm.cmd test`: 44 testes de componentes e 13 cenários de autenticação aprovados. Foi atualizada a expectativa antiga de cartões impressos e adicionado teste do relatório e de seus totais.
- `npm.cmd run build`: aprovado.
- Prévia visual da revisão gerada com o mesmo componente e CSS de impressão, usando seis registros representativos, em `backups/validacao-impressao-propriedades-estoque-20260921/previa.pdf`; renderização conferida sem cortes ou sobreposição. `pdfinfo`: uma página, 841,92 × 594,96 pt (A4 paisagem). A prévia do diálogo do navegador autenticado não ficou acessível no navegador integrado; a validação visual foi feita pelo PDF local.

Esta tarefa não inclui commit, push, merge ou publicação.

## Aplicação local na porta 5174

Após a revisão do layout, a imagem do usuário ainda mostrava os cartões e o mapa na impressão. O código estava correto, mas o contêiner local do frontend servia o pacote antigo (`index-zSALX8eR.js`). Antes de atualizar o ambiente, foi validado o backup `D:/PROJETOS/AGRO-AI-PRO/backups/agro-ai-pro-2026-09-21-180854-485895`, incluindo código não commitado, dump PostgreSQL e uploads. O serviço `frontend` foi reconstruído e recriado isoladamente com `FRONTEND_PORT=5174`. A resposta de `http://127.0.0.1:5174/` passou a servir `index-CTTtniz8.js` e `index-CZsd7jQ6.css`; o contêiner ficou saudável, a API retornou HTTP 200 e, após recarregar a página autenticada, o DOM continha a tabela nova com seis propriedades. Como o navegador integrado não expõe a janela de impressão, a conferência visual A4 continua baseada no PDF local gerado com o mesmo componente e CSS.
