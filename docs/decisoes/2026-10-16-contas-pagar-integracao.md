# Integração dos novos lançamentos ao Financeiro

## Escopo e decisões do Product Owner

Solicitado incorporar obrigações de pagamento ao Financeiro, retirar os cinco
cartões de resumo do Estoque e destacar contas a pagar em vermelho. Em 15/10,
o Product Owner escolheu integrar somente novos lançamentos; os antigos exigem
conferência prévia. Trabalho pausado e retomado por autorização em 16/10/2026.

- Despesas externas novas de Transportes geram uma conta a pagar pendente.
- Remunerações novas geram salário mais comissão calculada pelo holerite existente;
  receitas, despesas de AREIA/PEDRA e conferências de fretes atualizam a comissão.
- Manutenções novas geram obrigação ao serem concluídas com custo positivo.
- Integrações existentes de compras de insumos, cavaco e diesel são preservadas.
- Consumo do diesel no silo não gera outra obrigação: a compra já possui título.
  Custos de consumo/uso e previsões de operações não são novas compras.
- Valores zero não geram títulos fictícios. Uma origem possui no máximo um título.
- Sem vencimento específico, o novo vínculo usa a data da origem e registra a
  regra nas observações. O vencimento pode ser conferido no Financeiro e permanece
  preservado nas atualizações posteriores destas novas origens.
- Valores são corrigidos na origem; baixa manual permanece no Financeiro.
  Contas liquidadas impedem alterações de valor ou exclusão da origem.
- Exclusão/cancelamento da origem cancela a obrigação pendente, preservando o
  título. Cancelar diretamente esses novos títulos no Financeiro exige corrigir
  a origem para manter ambos os módulos consistentes.
- Históricos e importações de Transportes não são convertidos automaticamente.
  Compras antigas de insumos sem vínculo também aguardam conferência.

## Arquivos e migrations

`financeiro/integracao.py`, `eventos.py`, `apps.py`, `serializers.py`, `views.py`
e `test_integracao_origens.py`; modelos de Transportes e Máquinas;
`estoque/compra_financeiro.py` e `estoque/models.py`.

Migrations aditivas aplicadas: `transportes.0009`, `maquinas.0005` e
`estoque.0013_compra_integracao_novos`. A inclusão inicial do indicador usa False
para os registros já existentes e True como padrão somente para os novos.
Sem dependências novas, commit, push, merge ou publicação em produção.

Interface: `EstoquePage.tsx` remove os cartões; `FinanceiroPage.tsx` e
`styles.css` destacam o total, aba, identificação e valor de contas pendentes
a pagar em vermelho. Outros trabalhos locais foram preservados.

## Evidências e verificações

- Backup privado verificado na retomada: `backups/visual-20261016-070831`,
  com código e mudanças locais, uploads, PostgreSQL, patch e manifesto SHA-256;
  CRC do ZIP e catálogo do dump conferidos. Tentativas incompletas anteriores
  foram preservadas; somente esta cópia é considerada aprovada na retomada.
- 72 testes relacionados aprovados antes da pausa, com um skip de concorrência;
  depois, 95 testes de regressão aprovados. Os oito primeiros testes desta
  integração estão presentes nas duas baterias e não devem ser contados duas vezes.
- Na retomada, os 21 testes finais de `apps.financeiro.test_integracao_origens`
  e `apps.estoque.test_compra_financeiro.CompraFinanceiroTests` passaram em
  PostgreSQL exclusivo via `python scripts/test_backend_isolado.py`.
  Incluem os dois cenários adicionados imediatamente antes da pausa: bloqueio
  de cancelamento direto e compra antiga aguardando conferência.
- `manage.py check`: sem problemas; `makemigrations --check --dry-run`: sem
  diferenças; `migrate --check`: nenhuma migration pendente.
- Testes frontend, TypeScript e Vite aprovados por
  `docker compose -p agro-ai-pro build frontend` antes da pausa. Build local
  Windows encontrou EPERM em dist; build Docker concluiu sem esse bloqueio.
- Banco, Redis, backend e frontend existentes reiniciados após serem encontrados
  parados na retomada; serviços saudáveis e `/api/ready/` retornando `status: ok`.
- Arquivos realmente servidos em 5174 confirmam ausência dos cartões do Estoque
  e presença da classe/cor vermelha. Interface `b9d38aeec2fb`, versão
  `2026.10.15.1`, compilada em `2026-10-16T02:16:10.458Z`.
- Conferência de dados: 4.701 lançamentos antigos de Transportes e 106 remunerações,
  todos com integração automática desabilitada e sem títulos novos vinculados.
  Não foram criados lançamentos reais de teste nem baixas de pagamento nesta tarefa.

Limite: conferência visual autenticada é acompanhada pelo chat responsável
pela interface; aqui a versão ativa foi confirmada por HTTP e pelos artefatos
servidos. A incorporação dos históricos continua dependendo de conferência,
conforme escolha expressa do Product Owner.
