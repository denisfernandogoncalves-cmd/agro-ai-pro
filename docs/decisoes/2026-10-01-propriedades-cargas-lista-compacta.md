# Propriedades e cargas colhidas em uma linha — 01/10/2026

Atendidas as duas solicitações do Product Owner na branch
`codex/propriedades-impressao-a4-20260921`, checkout `.worktrees/runtime-origin-main`.

Alterado somente `frontend/src/styles.css`: cada propriedade mantém nome,
município/UF, área declarada, CAD/PRO, área calculada e diferença (quando houver),
além de Editar/Excluir, em uma linha. Cada carga mantém identificação, data,
transporte, produtora, CAD/PRO, cultura/safra, armazenagem, status, sacas,
pesos, descontos, análises, movimento e ações na mesma linha. Rateios de cargas
compartilhadas e motivos de cancelamento também continuam disponíveis.
As listas têm rolagem horizontal quando a largura da tela não comporta os dados.
Seleção, edição, exclusão e regras de negócio permanecem as existentes.

Backup privado antes das alterações:
`D:/PROJETOS/AGRO-AI-PRO/backups/sincronizacao-20261001-083927/`.
Inclui histórico, código e alterações dos 13 worktrees, configuração e uploads;
ZIPs e Git bundle verificados, hashes no manifesto. Banco em `postgres.dump`,
verificado com `pg_restore --list`, SHA-256 no manifesto próprio.

`npm run build`, `npm test`, `docker compose -p agro-ai-pro build frontend`
e `git diff --check` aprovados. Interface local atualizada com
`FRONTEND_PORT=5174 docker compose -p agro-ai-pro up -d --no-deps frontend`.
HTML, CSS das duas listas e API health verificados por HTTP 200.
Mantém-se o aviso preexistente de bundle maior que 500 kB; não há script de lint.
Não houve verificação visual na sessão particular do navegador do usuário.

Alterações locais anteriores preservadas. Nenhuma migration ou alteração de
dados necessária. Testes de backend não se aplicam à alteração de CSS.
Sem commit, push ou merge.
