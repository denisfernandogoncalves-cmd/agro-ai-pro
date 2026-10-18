# Ranking de resultado e eficiência dos motoristas — 13/10/2026

## Objetivo e critérios

Comparar motoristas por contribuição financeira e eficiência usando registros
existentes, sem criar custos, tarifas, distâncias, horas ou pesos fictícios.
Preservar salário, comissão e cálculos de transportes. Diferenciar faturamento,
resultado e margem; aplicar os filtros atuais e respeitar acesso às origens.
Não criar uma nota combinada com pesos arbitrários entre dinheiro e operação.

## Uso e cálculo

Transportes → Relatórios e ranking → aplicar período/placa/motorista.

- Financeiro: maior receita menos despesas operacionais, salários e comissões.
  Inclui comissões de fretes previamente marcadas para adicionar. Desempate por
  receita e nome; resultados negativos permanecem negativos e são identificados.
- Eficiência financeira: maior margem (resultado / receita × 100). Sem receita,
  não há margem comparável. Desempate por resultado e nome.
- Indicador operacional: maior carga média (toneladas / documentos ativos) de
  cargas colhidas e entregas de vendas autorizadas, com volume e número de documentos.
  Desempate pelo volume e nome. Não é contagem de viagens físicas únicas nem
  produtividade por distância/tempo; capacidade do veículo não está cadastrada.

Valores financeiros reagrupam nomes equivalentes por caixa/espaços somente no
ranking, sem alterar os cadastros e os relatórios anteriores. Documento usa o
motorista histórico da origem ou a associação manual da conferência de fretes.
Placa ausente pode ser identificada pela associação manual existente. Origens
canceladas/substituídas ficam fora; documentos sem motorista são contados como
pendentes e não ganham um motorista fictício.

A tela destaca líderes por resultado e margem; mostra tabelas, critério detalhado,
falta de remuneração mensal/despesa registrada, impressão e exportação CSV.
Ranks são separados: maior faturamento não é maior resultado, e maior margem não
é necessariamente maior valor financeiro. Os rankings antigos de faturamento
por placa/motorista foram preservados.

## API e arquivos

GET /api/transportes/lancamentos/relatorio/ inclui ranking_financeiro,
ranking_eficiencia, ranking_operacional, criterio_ranking e documentos_sem_motorista.
Filtros existentes data_inicio/data_fim/caminhao/motorista/placa são preservados.
Consultar em transportes é obrigatório; informação operacional requer consultar
em cargas/vendas, conforme a origem. Exportação exige imprimir em transportes.

Arquivos: backend/apps/transportes/{ranking,test_ranking,views}.py;
frontend/src/api/transportes.ts;
frontend/src/pages/Transportes/{RankingMotoristas,TransportesPage}.tsx;
docs/SPRINTS.md. Sem novos modelos, migrations ou dependências nesta tarefa.

## Validação e preservação

- Backup inicial: backups/agro-ai-pro-2026-10-13-221752-808737.
- Antes de atualizar: backups/agro-ai-pro-2026-10-13-222249-995868.
  Código/alterações anteriores, banco e uploads verificados com hashes.
- python scripts/test_backend_isolado.py apps.transportes apps.relatorios:
  61 casos, OK, um skip de planilha privada (27,184 s), PostgreSQL exclusivo.
- Casos novos: receita alta com resultado baixo, margem e resultado com líderes
  diferentes, salário/comissão deduzidos, prejuízo, receita ausente, nomes
  equivalentes, período/placa, CSV, acesso, volume médio e cancelamento.
- Docker build frontend: testes, TypeScript e Vite aprovados.
- Django check e makemigrations --check --dry-run aprovados; nenhuma mudança.
- Frontend 5174 atualizado e saudável; diff revisto sem erros. Consulta operacional
  do relatório em leitura confirmou resposta 200 e os três conjuntos de rankings,
  sem alterações em lançamentos ou remunerações.

## Limites e atenção

Resultado representa somente receitas/custos cadastrados em Transportes, não lucro
contábil certificado, saldo bancário ou valor comercial do grão. O frete preenchido
na conferência não gera receita automaticamente: lançar sua receita uma única vez
em Transportes. Custos ausentes podem mudar a classificação, mesmo quando há
algum lançamento de despesa. Para mês, escolher primeiro até último dia: salário e
comissão mantêm a regra de contabilização no último dia da competência.

O indicador operacional contempla documentos de grãos acessíveis ao usuário,
sem medir outros serviços/mercadorias, km/L, produtividade por hora ou ocupação.
Dois documentos podem representar a mesma viagem física; maior carga média não
prova eficiência geral. Distância, combustível, horas e capacidade precisam de
registros próprios para essas métricas. Sem teste de carga, conferência visual
integral ou impressão física. Mudanças anteriores de holerite/fretes preservadas.
Sem commit, push, merge, publicação ou serviços pagos nesta etapa.
