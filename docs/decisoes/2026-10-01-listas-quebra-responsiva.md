# Listas compactas com quebra conforme a tela — 01/10/2026

A orientação mais recente do Product Owner substitui a linha única com rolagem
horizontal: aproveitar uma linha quando couber e passar às linhas seguintes
conforme a largura disponível, mantendo todos os dados e ações visíveis.
Aplica-se às listas de vendas, propriedades e cargas colhidas, inclusive rateios.

Alterado `frontend/src/styles.css` na branch
`codex/propriedades-impressao-a4-20260921`, checkout `.worktrees/runtime-origin-main`.
Removidos `min-width: max-content`, `white-space: nowrap` e a rolagem horizontal
das três listas; aplicada quebra flexível também aos grupos internos.
Textos longos podem quebrar, cartões respeitam a largura disponível e botões
acompanham o fluxo. Telas pequenas podem precisar de mais de duas linhas.
Nenhuma informação ou funcionalidade foi removida.

Backup privado verificado antes das alterações:
`D:/PROJETOS/AGRO-AI-PRO/backups/sincronizacao-20261001-085655/`, com código,
alterações locais, histórico, configuração, uploads e dump PostgreSQL.
ZIPs/bundle e `pg_restore --list` verificados; hashes nos manifestos.

`npm run build`, `npm test`, build Docker e `git diff --check`: aprovados.
Interface atualizada na porta 5174; HTML, CSS atualizado e API health: HTTP 200.
Sem verificação visual na sessão particular do navegador do usuário.
Aviso preexistente de bundle acima de 500 kB; não há script de lint.
Nenhuma migration ou alteração de dados; testes de backend não se aplicam.
Alterações anteriores preservadas; sem commit, push ou merge.
