# Estoque — compras por embalagens

## Escopo aprovado

Branch `codex/grupos-propriedades-colheita`, checkout `.worktrees/runtime-origin-main`.
Preservadas alterações locais anteriores. Implementados os 12 campos solicitados
no formulário e na tabela, incluindo Cultura e excluindo Produtor conforme
orientação posterior. Data de vencimento é o pagamento da compra.

## Implementação

Criado `CompraEstoque`, ligado por OneToOne à movimentação de entrada. A compra
preserva as embalagens, seu conteúdo e custo; o movimento mantém a quantidade
e o custo na unidade base para os saldos e saídas existentes. Lote, movimento
e compra são gravados na mesma transação. UUID e assinatura impedem duplicação
por reenvio e rejeitam conteúdo conflitante.

143 embalagens de 5 litros a R$ 370,00 resultam em 715 litros, R$ 74,00/litro e
R$ 52.910,00. Total monetário calculado diretamente pelas embalagens; o custo
por litro/kg pode ser arredondado para quatro casas sem alterar esse total.

Vencimento fica separado da validade e não gera título financeiro. Registros
antigos não são reinterpretados como compras; permanecem consultáveis em
Outras movimentações, saldos e rastreabilidade.

## Arquivos desta entrega

Criados:
- `backend/apps/estoque/compras.py`: API, validação e gravação atômica.
- `backend/apps/estoque/compras_calculos.py`: cálculos decimais.
- `backend/apps/estoque/test_compras.py` e `test_compras_calculos.py`.
- `backend/apps/estoque/migrations/0003_compraestoque.py`.
- `frontend/src/pages/Estoque/ComprasEstoque.tsx`.
- Este relatório.

Alterados: `backend/apps/estoque/models.py`, `urls.py`,
`frontend/src/api/estoque.ts`, `frontend/src/pages/Estoque/EstoquePage.tsx`,
`frontend/src/styles.css`, `docs/api/ESTOQUE.md` e `docs/SPRINTS.md`.
Nenhum arquivo removido; nenhuma dependência adicionada.

## Backups verificados

Dentro deste checkout:
- `backups/agro-ai-pro-2026-09-14-071526-672141`: antes das alterações.
- `backups/agro-ai-pro-2026-09-14-123301-479389`: antes da migration e atualização local.

Ambos incluem código e mudanças locais, uploads, dump PostgreSQL e estado Git.
Seis arquivos por manifesto; leitura integral do dump via pg_restore sem
restauração, CRC dos ZIPs e hashes SHA256 registrados em `manifesto.json`.

## Verificação

- `manage.py test apps.estoque apps.relatorios --settings=config.settings.test --noinput`: 50 testes aprovados após corrigir a escala decimal da quantidade.
- `manage.py makemigrations --check --dry-run --settings=config.settings.test`: nenhuma alteração pendente.
- `docker compose -p agro-ai-pro exec -T -e POSTGRES_DB=estoque_compra_20260914_0730 -w /app/backend backend python manage.py test apps.estoque apps.relatorios --keepdb --noinput`: mesmos 50 testes aprovados em banco isolado, preservado.
- `npm.cmd test`: 40 testes de componentes e 13 cenários de autenticação aprovados.
- `npm.cmd run build` e build Docker do frontend: aprovados.
- `docker compose -p agro-ai-pro exec -T -w /app/backend backend python manage.py migrate estoque`: migration 0003 aplicada com sucesso, apenas criação de tabela.
- Frontend reconstruído e iniciado na porta 5174; página HTTP 200 e `/api/health/` com status ok.
- Navegador real: 12 colunas na ordem pedida; Produtor ausente; campos e seletores carregados; prévia de 143 × 5 × R$ 370 validada sem gravar dados no banco do usuário.
- Corrigida largura do grid após a inspeção visual: em viewport de 1280 px, página de 1265 px (área útil), tabela de 1480 px contida em área rolável de 1161 px. Formulário sem corte horizontal.
- `git -c core.safecrlf=false diff --check`: aprovado.

Cobertura nova inclui rejeição de números inválidos, precisão, autenticação,
busca, fornecedor inativo, unidade incompatível, reenvio sem duplicação,
conflito de chave, rollback integral e saída com bloqueio de saldo insuficiente.

## Limitações e Git

Produtos da compra em embalagens usam litros/kg. Demais unidades permanecem no
fluxo de movimentações existente. Quantidade até três casas decimais; valor
unitário até quatro. Cultura e vencimento são opcionais. O aviso preexistente
de bundle maior que 500 kB permanece; não há script lint no package.json.
Validação visual realizada no viewport desktop disponível, sem teste exaustivo
de dispositivos. Não foram criadas compras de exemplo no banco do usuário.

Sem commit, push ou merge. Sem exclusão ou restauração de dados.
