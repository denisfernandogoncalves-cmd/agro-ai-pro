# Vendas de grãos com ou sem contrato

Solicitação do Product Owner em 31/08/2026: permitir a venda independentemente
da existência de contrato. Esta autorização substitui a exigência anterior de
contrato no formulário. Não altera as demais regras de estoque e rastreabilidade.

Checkout: `D:/PROJETOS/AGRO-AI-PRO/.worktrees/runtime-origin-main`.
Branch: `codex/remover-grupos-colheita`; HEAD inicial `8a0c862`.
Alterações anteriores e o checkout principal foram preservados. Entrega
incremental; o índice das Sprints já concluídas permanece inalterado.

## Critérios de aceite e resultado

- Nova venda aceita **Sem contrato**, opção inicial do seletor. Não exige
  cadastro de contrato, número fictício ou empresa vinculada a contrato.
- Na saída sem contrato, o destino informado identifica o comprador. No
  rascunho, o comprador é preenchido diretamente. Identificação vazia é rejeitada.
- Com contrato selecionado, continuam sendo usados seu número e empresa;
  a quantidade sugerida pode ser ajustada.
- API aceita contrato ausente ou nulo e número ausente ou vazio. A venda
  permanece rastreável por ID, posição oficial, comprador e movimentos.
- Saída sem contrato debita o estoque, inclusive permitindo saldo negativo
  conforme autorização anterior. Repetição do envio não duplica a venda;
  reutilização da chave com conteúdo diferente é rejeitada.
- Edição, exclusão lógica com estorno e criação de rascunho sem contrato foram
  verificadas. Listas, detalhes e relatórios exibem “Sem contrato” quando aplicável.

## Backups e atualização local

Backups privados, ignorados pelo Git, sem sobrescrever os backups anteriores:

- `backups/retomada-2026-08-31-075837-452576/`: antes das alterações.
- `backups/retomada-2026-08-31-080221-086813/`: antes da migration e atualização.

Cada pasta contém código atual (inclusive não commitado), banco PostgreSQL em
formato custom, uploads, estado/diff Git, catálogo e manifesto com tamanhos e
SHA-256. ZIPs verificados por CRC; banco lido integralmente com pg_restore sem
restauração. O ZIP de uploads está vazio porque não havia arquivos nessa pasta.

Aplicada `vendas.0007_numero_contrato_opcional`, que permite número em branco
na validação do modelo, sem reescrever registros existentes. Frontend reconstruído
e atualizado no Compose `agro-ai-pro`, mantendo a porta local 5174. Nenhuma venda
real enviada pelo agente; nenhuma restauração ou exclusão de dados existentes.

## Arquivos desta alteração

- `backend/apps/vendas/models.py`: número opcional e representação sem contrato.
- `backend/apps/vendas/serializers.py`: contrato/número opcionais; comprador ou destino.
- `backend/apps/vendas/services.py`: criação sem exigir número contratual.
- `backend/apps/vendas/migrations/0007_numero_contrato_opcional.py`: nova migration.
- `backend/apps/vendas/test_sem_contrato.py`: cinco testes de integração novos.
- `frontend/src/pages/Vendas/VendasPage.tsx`: criação e exibição sem contrato.
- `frontend/src/pages/Vendas/CamposTransporteVenda.tsx`: destino obrigatório quando necessário.
- `frontend/src/pages/Vendas/EditorLancamentoVenda.tsx`: comprador editável sem contrato.
- `frontend/src/pages/Relatorios/RelatoriosPage.tsx`: identificação legível sem número.
- `frontend/scripts/test-components.mjs`: regressão do seletor opcional.
- `docs/api/VENDAS.md` e este relatório: regras, exemplo e evidências.

## Validação

Comandos Docker executados no checkout acima, com projeto `agro-ai-pro`:

- `docker compose -p agro-ai-pro exec -T -w /app/backend backend python manage.py test apps.vendas.test_sem_contrato apps.vendas.test_saida_completa --noinput`:
  **13 testes aprovados** em PostgreSQL.
- `docker compose -p agro-ai-pro exec -T -w /app/backend backend python manage.py test --noinput`:
  **334 testes encontrados: 329 aprovados e 5 ignorados**, 175,740 segundos.
- `manage.py makemigrations --check --dry-run`: nenhuma alteração detectada.
- `manage.py migrate --noinput`: migration 0007 aplicada com sucesso.
- `manage.py check` e `manage.py migrate --check`: aprovados após atualização.
- `npm.cmd test` no frontend: **40 cenários gerais e 13 de autenticação aprovados**.
- `npm.cmd run build` e `docker compose -p agro-ai-pro build frontend`: aprovados.
- `$env:FRONTEND_PORT='5174'; docker compose -p agro-ai-pro up -d --no-deps frontend`:
  frontend local atualizado.
- `git -c core.safecrlf=false diff --check`: aprovado.
- Navegador: seletor sem `required`, “Sem contrato” selecionado; destino obrigatório
  sem contrato; formulário preenchido sem contrato com zero campos inválidos;
  alternância para contrato cadastrado e retorno para “Sem contrato” validada.
  Nenhum erro de console. Validação em aba separada, sem enviar formulário nem
  recarregar a aba do usuário.

## Limitações e pendências

- Cinco testes da suíte foram ignorados; isso está refletido na contagem acima.
- Permanece o aviso preexistente de bundle maior que 500 kB; não há script
  separado de lint no frontend. TypeScript e build aprovados.
- As vendas de teste foram executadas em banco de testes, não na base de uso.
- Revisão final deve considerar que o worktree contém alterações anteriores
  ainda não commitadas. Sem commit, push, merge ou publicação em produção.
- Quem estiver com a versão antiga aberta precisa atualizar a página para
  carregar o novo formulário, anotando antes os dados ainda não enviados.
