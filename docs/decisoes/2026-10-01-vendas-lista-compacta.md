# Vendas registradas em uma linha — 01/10/2026

Solicitação: compactar os cartões de vendas, cujas informações e botões
ocupavam várias linhas e deixavam espaços desproporcionais.

Branch: `codex/propriedades-impressao-a4-20260921`, no checkout
`.worktrees/runtime-origin-main`, responsável pela interface na porta 5174.
Alterações anteriores preservadas.

Arquivos: `frontend/src/pages/Vendas/VendasPage.tsx` identifica a seção com
`vendas-lista-compacta`; `frontend/src/styles.css` aplica alinhamento horizontal
ao status, contrato/destino, identificação, quatro quantidades e ações.
Margens e espaçamentos reduzidos. Em telas menores, a própria lista permite
rolagem horizontal; nenhuma informação é ocultada. As regras são restritas
à lista de vendas e não alteram o detalhe nem a impressão.

Backup privado: `D:/PROJETOS/AGRO-AI-PRO/backups/sincronizacao-20261001-083553/`,
com histórico Git, código e alterações dos 13 worktrees, configuração e uploads,
ZIPs verificados e hashes registrados. Banco em `postgres.dump`, verificado
por `pg_restore --list`, com SHA-256 em `manifesto-dump.json`.

Validações: `npm run build`, `npm test`, build Docker do frontend e
`git diff --check` aprovados. Permanece o aviso preexistente de bundle acima de
500 kB. Não há script de lint. Não foram necessários testes de backend ou
migrations, pois a alteração é exclusivamente de apresentação.

Interface local atualizada via `FRONTEND_PORT=5174 docker compose -p agro-ai-pro up -d --no-deps frontend`.
HTML, CSS atualizado e API health conferidos por HTTP. Não houve verificação
visual na sessão particular do navegador do usuário.
Sem alteração de dados, commit, push ou merge.
