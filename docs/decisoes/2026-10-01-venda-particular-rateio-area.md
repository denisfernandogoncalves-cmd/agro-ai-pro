# Venda PARTICULAR com rateio por área

Implementado em 01/10/2026 na branch `codex/propriedades-impressao-a4-20260921`,
checkout `.worktrees/runtime-origin-main`, que atende o aplicativo na porta 5174.
As alterações locais preexistentes em estoque, faturamento e transferências foram preservadas.

## Regra aprovada e comportamento

O Product Owner solicitou que o destino PARTICULAR desconte a quantidade de
todas as propriedades e confirmou que a proporção deve usar a área, e não o saldo.
O formulário reconhece PARTICULAR sem distinguir maiúsculas ou espaços externos.
Em venda com saída, substitui os seletores obrigatórios de propriedade e posição
por produto, safra, classificação e armazenagem comuns. A prévia mostra todas
as propriedades, seus CAD/PROs, áreas e descontos antes de habilitar o registro.
Rascunhos e outros destinos continuam com a origem individual.

A quantidade de cada propriedade é `peso total × área / soma das áreas`.
O método de maiores restos distribui os gramas restantes, mantendo a soma exata
e nenhuma parcela negativa. Parcelas arredondadas para zero constam na prévia,
mas não geram movimentação. Cada propriedade precisa ter área positiva e um
único vínculo ativo com CAD/PRO ativo; vínculos ausentes ou ambíguos geram erro
identificando a propriedade, sem omiti-la silenciosamente.

Todas as propriedades participam, independentemente do saldo. Se não houver
posição para as dimensões informadas, o serviço existente cria a posição e seu
lote operacional sem crédito fictício. Mantém-se a permissão preexistente de
saldo negativo por sobra técnica. Cultura, safra e classificação devem ser
conferidas pelo usuário para descontar a posição desejada.

## Integridade e histórico

A migration aditiva `vendas.0008_rateio_venda_particular`, aplicada localmente,
cria o registro agrupador e um vínculo opcional nas vendas. Não altera vendas
históricas. Cada parcela usa o fluxo existente de venda/reserva/entrega e fica
visível nas vendas e nos relatórios de sua propriedade; o grupo guarda as áreas,
os pesos, os CAD/PROs e os IDs das parcelas utilizados no lançamento original.
Correções, devoluções e exclusões existentes afetam a parcela selecionada,
conforme indicado no detalhe; o snapshot original permanece histórico.

Registro transacional: uma falha reverte todas as parcelas. A chave de
idempotência impede reenvios duplicados, inclusive simultâneos, e rejeita
reutilização com dados diferentes. Uma prévia que mudou antes do registro é
rejeitada; nesse caso, atualizar a página e conferir novamente os valores.
Bloqueios seguem a ordem de CAD/PRO e armazenagem usada pelo ledger.

## Backup

Pasta privada ignorada pelo Git:
`D:/PROJETOS/AGRO-AI-PRO/backups/sincronizacao-20261001-074932/`.
O procedimento existente preservou o histórico Git, o código dos 13 worktrees,
mudanças não commitadas, configuração privada e uploads; verificou os ZIPs e
registrou hashes SHA-256 em `manifesto.json`. `postgres.dump` preservou o banco
antes das alterações; `postgres-pre-migration.dump` foi gerado imediatamente
antes da migration. Ambos foram verificados com `pg_restore --list` e possuem
manifestos SHA-256 próprios. Nenhum backup anterior foi sobrescrito.

## Arquivos e validações

Backend: `models.py`, `selectors.py`, `serializers.py`, `views.py`,
`particular_services.py`, `test_particular.py` e migration 0008 em `apps/vendas`.
Frontend: `src/api/vendas.ts`, `src/pages/Vendas/VendasPage.tsx` e
`scripts/test-venda-particular.mjs`.

- `manage.py test apps.vendas.test_particular apps.vendas.test_saida_completa apps.vendas.test_saldo_negativo apps.vendas.test_sem_contrato --settings=config.settings.test --noinput`:
  32 testes, aprovados; três cenários exclusivos do PostgreSQL ignorados em SQLite.
- `call_command('test', 'apps.vendas', interactive=False)` com banco PostgreSQL
  isolado `test_particular_20261001_0800`: 74 testes aprovados, incluindo concorrência.
- `manage.py check`: aprovado.
- `manage.py makemigrations --check --dry-run --settings=config.settings.test`:
  nenhuma mudança pendente.
- `npm run build`, `npm test` e `node scripts/test-venda-particular.mjs`: aprovados.
  Não há script de lint. O build informa o aviso preexistente de bundle acima de 500 kB.
- `docker compose -p agro-ai-pro build frontend` e
  `FRONTEND_PORT=5174 docker compose -p agro-ai-pro up -d --no-deps frontend`:
  interface local atualizada. Interface, bundle atualizado e health da API pelo
  proxy verificados com HTTP 200.
- Prévia autenticada com os dados atuais, sem alterar vendas ou movimentações:
  50 kg resultam em SAGRILO 12,687 kg, FAZENDA ELECTRA 32,763 kg e
  PEDRO CARIOCA 4,550 kg. Consulta de vendas: HTTP 200.
- Revisão dos diffs da tarefa e `git diff --check`: aprovados.

Nenhuma venda real foi lançada durante a validação. Não foi realizada uma venda
na sessão particular do navegador do usuário; o fluxo completo foi validado nas
APIs dos bancos de teste. Não houve commit, push ou merge.
