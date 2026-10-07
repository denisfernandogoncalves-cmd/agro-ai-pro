# Layout global das abas — 21/09/2026

## Objetivo

Padronizar cores, tipografia e componentes visuais de todas as abas do
AGRO-AI-PRO, mantendo os formulários, fluxos de negócio e impressão existentes.

## Decisão

- Usar uma paleta verde agrícola com fundo neutro, cartões claros e cor de foco
  âmbar. As cores centrais ficam em variáveis CSS em `frontend/src/styles.css`.
- Usar a fonte de interface do sistema (`Segoe UI` no Windows, com alternativas
  locais). Não há dependência de fonte externa nem alteração de `package-lock`.
- Destacar o módulo atual na navegação, melhorar o cabeçalho, espaçamento,
  botões, campos, tabelas, mensagens e estados de foco em CSS compartilhado.
- Preservar o layout de impressão em `frontend/src/print.css` e alinhar as cores
  do navegador e do PWA à nova paleta.
- No celular, a navegação permanece rolável na horizontal e os cartões e ações
  ocupam a largura disponível.

## Escopo e impacto

`frontend/src/App.tsx`, `frontend/src/styles.css`, `frontend/src/print.css`,
`frontend/index.html` e `frontend/public/manifest.webmanifest`.
Todas as 16 abas usam o mesmo cabeçalho, navegação e regras visuais base.
Nenhum modelo, endpoint, migration ou dado foi alterado.

## Verificação

Backup privado anterior à edição: `backups/agro-ai-pro-2026-09-21-134052-306409`,
com código, uploads, banco e hashes registrados no manifesto.

- `npm test`: 44 testes de componentes e 13 cenários de autenticação aprovados.
- `npm run build`: aprovado. O aviso preexistente de bundle acima de 500 kB
  continua presente.
- Tela de entrada conferida no navegador em largura estreita; abas autenticadas
  Propriedades, Financeiro, Estoque, Cargas colhidas e Relatórios conferidas
  em `http://127.0.0.1:5174/` após iniciar os serviços locais.
- `git diff --check`: aprovado.

O botão de atualização de grupos em Cargas foi alinhado à base do campo, após
inspeção visual. Os serviços locais foram iniciados com backup prévio, a API
`/api/health/` respondeu com sucesso e a porta 5174 passou a servir o layout
novo. Não há migrations novas; não foram necessários testes backend específicos,
pois só houve alterações de apresentação no frontend.
