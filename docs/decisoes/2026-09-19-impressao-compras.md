# Impressão somente de compras de estoque — 19/09/2026

Solicitação: imprimir somente a tabela Compras de estoque mostrada na imagem.
Branch: codex/grupos-propriedades-colheita, checkout runtime-origin-main.

Alterados: frontend/src/pages/Estoque/ComprasEstoque.tsx (identificador da seção),
frontend/src/print.css (seleção da tabela, A4 paisagem e quebra de textos) e
docs/api/ESTOQUE.md. Mantém as linhas filtradas e todas as colunas da tabela,
incluindo Valor total. Oculta demais seções do Estoque e cabeçalho do aplicativo.

Backup validado de código, banco e uploads:
D:/PROJETOS/AGRO-AI-PRO/backups/agro-ai-pro-2026-09-19-125545-277880.

Validação: npm test (44 testes de componentes, 13 cenários de autenticação),
npm run build, docker compose -p agro-ai-pro build frontend e diff --check aprovados.
Frontend recriado na porta 5174. Sem alterações de banco ou migrations.
Não houve inspeção visual do diálogo de impressão; configurações de cabeçalhos
próprios do navegador continuam sob controle do usuário. Aviso preexistente de
bundle acima de 500 kB permanece. Sem commit, push ou merge.
