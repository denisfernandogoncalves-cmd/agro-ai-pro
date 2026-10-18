# Compras, estornos e consulta financeira — 16/10/2026

## Objetivo e critérios

Compra de insumos gera uma conta a pagar vinculada; estorno reduz quantidade e
valor líquido na mesma transação. Cancelamento integral cancela título pendente.
Compra paga gera crédito a receber do fornecedor, conforme escolha expressa do
Product Owner. Histórico e pagamentos permanecem preservados; reenvios não duplicam.
Consulta financeira aproveita a largura da linha e não apresenta Ajuda nesta aba
nem Meus filtros favoritos. Filtros normais e arquivos favoritos salvos preservados.

## Implementação

- `estoque/compra_financeiro.py`: valor proporcional sobre o total original,
  arredondamento acumulado em centavos; título único; crédito por estorno vinculado.
  Estorno feito antes do pagamento não volta a ser creditado depois de pagar.
  Crédito limitado ao valor pago; pagamento original não é apagado nem baixado outra vez.
- `estoque/compras.py`, `models.py`, `services.py`: criação/estorno atômicos,
  valores original/estornado/líquido/a pagar, proteção da exclusão física.
- Financeiro protege edição de valores da origem e cancelamento direto da conta
  de compra: cancelar pela compra mantém estoque e obrigação consistentes.
- `ComprasEstoque.tsx` e API: quantidade líquida em embalagens e litros/kg,
  original destacado, valor líquido e título vinculado.
- `styles.css`: linhas financeiras compactas no desktop, ações alinhadas e
  adaptação para telas menores, preservados estilos de contas a pagar em vermelho.
- `FinanceiroPage.tsx` e `App.tsx`: retirada da ajuda e favoritos somente do Financeiro.
- Migration aditiva `estoque.0012_compra_financeiro` aplicada. Migration
  `estoque.0013_compra_integracao_novos`, criada pelo trabalho paralelo de contas
  a pagar, preservada e aplicada para compatibilidade: registros antigos sem
  vínculo não integram automaticamente; novos integram por padrão. ANKOR foi
  conferida e vinculada expressamente nesta tarefa.

Sem vencimento, a conta usa a data da compra, com regra explícita nas observações.
Compras de valor zero não criam título fictício. Liquidação continua manual no
Financeiro; a indicação de pagamento já existente na origem é preservada.
Os lançamentos históricos gerais de outros módulos não foram importados por esta tarefa.

## Compra real conferida

Compra ANKOR `51cda382-56b1-4666-9f0f-0acb6d5469d9`, AGRO PRODUZ:
original 2.500 L / R$ 125.000,00; estorno já registrado pelo usuário de 500 L /
R$ 25.000,00; líquido 2.000 L / R$ 100.000,00. Título financeiro #41, pendente,
vencimento 02/07/2027. Nenhum estorno real criado por teste.

Script `scripts/integrar_compras_financeiro.py`: ensaio com rollback padrão,
confirmação apenas com `APLICAR=True`, auditoria técnica explícita sem atribuir
sessão humana. Ensaio, aplicação e conferência do vínculo aprovados.
API autenticada retornou HTTP 200 e exatamente um título ANKOR de R$ 100.000,00.

## Backups e verificações

Backups privados de código, alterações locais, banco e uploads, ZIP CRC,
catálogo do dump e SHA-256 verificados:
`backups/visual-20261015-230826`, `231337`, `231611` e
`backups/visual-20261016-060613` (os dois nomes abreviados usam o prefixo
`visual-20261015-`). Backups anteriores preservados.

- 72 testes PostgreSQL isolado aprovados: `docker compose exec -T backend python
  scripts/test_backend_isolado.py apps.estoque.test_compra_financeiro.CompraFinanceiroTests
  apps.estoque.test_compras apps.estoque.test_estornos_compra apps.financeiro.tests
  apps.estoque.test_faturamento`.
- Dois testes antigos ajustados à criação da conta e bloqueio da exclusão física;
  salvamento atômico necessário por permissões de escrita do arquivo, sem alteração de ACL.
- `manage.py check` aprovado; `makemigrations --check --dry-run` sem diferenças.
- `docker compose -p agro-ai-pro build frontend`: testes frontend, TypeScript e
  Vite aprovados. Frontend ativado em 5174; `/api/ready/` retorna status ok.
- Revisão localizada e `git diff --check` aprovados. Sem conferência visual
  autenticada no navegador; validação de apresentação limitada ao código e build.

Branch `codex/modernizacao-visual-runtime`, preservados os trabalhos locais
preexistentes. Sem commit, push, merge ou publicação em produção.
