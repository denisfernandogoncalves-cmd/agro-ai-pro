# Compras de diesel e abastecimento no silo

**Atualização:** exclusão lógica, vencimento em dia útil, retirada da média e
contas a pagar foram acrescentados conforme [integração financeira](2026-10-15-cavaco-diesel-financeiro.md).
As regras dessa atualização substituem os limites anteriores abaixo.

## Escopo e aceite

Entrega na branch operacional `codex/modernizacao-visual-runtime`, que serve o
AGRO IA local. Preservar alterações anteriores das duas árvores; sem merge,
commit ou push. Acrescentar em Transportes a aba Compras de diesel, cadastro,
edição versionada, filtros por período, fornecedor, produtor, tipo e pagamento,
resumo de todos os resultados filtrados e paginação de 50 linhas.

Em Inserir receita / despesa, despesas permitem marcar Abasteceu no silo,
informar S10/S500 e litros. O backend calcula o custo e os relatórios existentes
o computam uma única vez como despesa operacional da placa/motorista/data.

## Regra aprovada pelo Product Owner

Em 15/10/2026 o usuário escolheu **Preço da última compra até a data do
abastecimento**. A média ponderada aparece somente no resumo das compras.

- Buscar a compra de mesmo tipo com data menor ou igual ao abastecimento.
- Havendo mais de uma compra no mesmo dia, usar a última cadastrada (maior ID).
- Sem compra anterior, bloquear e orientar o cadastro; nunca usar preço zero
  nem compra futura ou de outro tipo.
- Unidade L e local Silo são definidos no servidor. O preço informado pelo
  cliente não substitui o preço da compra.
- Gravar referência e preço na despesa. Novas compras e correções de preço
  não recalculam despesas já salvas. Alterar a data ou tipo do abastecimento
  recalcula; alterar só litros ou descrição mantém o preço salvo.
- Prévia informa data da compra e preço. Se a referência/preço mudar entre
  consulta e gravação, bloquear para nova conferência.
- Total arredondado por lançamento a centavos, com Decimal/ROUND_HALF_UP.

## Arquivos principais e API

- `backend/apps/maquinas/models.py`: CompraDiesel; migration aditiva 0002.
- `backend/apps/maquinas/diesel.py`: serializer, filtros, CRUD sem exclusão,
  resumo; publicação por `transportes/urls.py`.
- `backend/apps/transportes/models.py`: campos opcionais aditivos e FK PROTECT
  para compra; migration 0008, sem reclassificar despesas anteriores.
- `backend/apps/transportes/diesel.py`, `serializers.py`, `views.py`: preço,
  snapshot e prévia autenticada.
- `backend/apps/core/auditoria.py`: campos de diesel e módulo da auditoria.
- `frontend/src/api/diesel.ts`, `api/transportes.ts`,
  `pages/Transportes/ComprasDiesel.tsx`, `TransportesPage.tsx`: interface e API.
- `backend/apps/transportes/test_diesel.py`: testes de compra, filtros,
  totais, autenticação/permissões, última compra, ausência, futuro, empate,
  preço da prévia alterado, edição concorrente e despesa manual preservada.

Endpoints autenticados, com as permissões já existentes de Transportes:

- `GET/POST /api/transportes/compras-diesel/`;
- `GET/PATCH/PUT /api/transportes/compras-diesel/{id}/`;
- `GET /api/transportes/compras-diesel/resumo/`;
- `GET /api/transportes/lancamentos/preco-silo/?data=AAAA-MM-DD&tipo_diesel=S10`;
- `POST/PATCH /api/transportes/lancamentos/`: abasteceu_silo, tipo_diesel e
  quantidade; na edição, versao_correcao_original. Referência e preço esperado
  opcionais protegem a prévia; compra_diesel e total são somente leitura.

Filtros das compras: data_inicio, data_fim, fornecedor, produtor, tipo,
pagamento, search e ordering. Paginação com page/page_size; resumo sem limitar
à página. Prazo em dias corridos, opcional; pagamento original desconhecido
permanece Não informado. Não são criados pagamentos, estoque ou contas a pagar
automaticamente. Não há baixa de estoque/controle de saldo físico do silo.
Há um silo compartilhado; produtor identifica a compra e pode ser filtrado,
mas não separa estoques ou tabelas de preço.

## Validação e operação

- Backups iniciais privados, ZIP/dump e hashes verificados:
  `backups/visual-20261015-154634-472468` (árvore principal) e
  `backups/visual-20261015-154658` (runtime).
- 102 testes PostgreSQL de Transportes, Máquinas e accounts aprovados (um skip).
- TypeScript/Vite aprovado com `npm run build -- --outDir ../backups/diesel-build`.
  O dist anterior possui arquivo sem permissão de exclusão; build alternativo
  privado validou a compilação sem remover artefatos anteriores.
- Backup renovado antes das migrations/dados:
  `backups/visual-20261015-173718`, ZIP e catálogo do dump aprovados, manifesto
  com hashes. Migrations maquinas.0002 e transportes.0008 aplicadas com sucesso.
- `npm test`: componentes/submissão, 16 cenários de autenticação, seis de
  rascunhos, usabilidade, coordenadas e romaneios aprovados. A primeira tentativa
  teve EACCES no servidor de testes; a execução autorizada fora do sandbox passou.
- `docker compose -p agro-ai-pro build frontend`: aprovado; interface ativada
  com FRONTEND_PORT=5174, mantendo o endereço original. Backend, PostgreSQL,
  Redis e frontend saudáveis. Asset ativo contém a aba Compras de diesel.
- Teste adicional de auditoria da compra aprovado após incluir o módulo
  Transportes no histórico. `git diff --check` sem erros de whitespace.
- Fonte CONTROLE DE DIESEL ICMS.xlsx preservada, SHA256
  `f13eda035eb18561f0975d1911a6566529bd3462e99ae04fb3ed8a874c3b19cc`.
  Duas compras importadas após validação/dry-run: S10 em 06/10/2026,
  6.000 L a R$ 7,12, e S500 em 08/10/2026, 6.000 L a R$ 7,09; GP/NEI,
  prazo 15 dias, pagamento Não informado. Total 12.000 L / R$ 85.260,00.
  Importação transacional registrada na auditoria como operação de importação,
  sem atribuição falsa a usuário humano. Artefatos privados em
  `backups/diesel-fonte-20261015`. Nova simulação encontrou zero compras novas,
  demonstrando prevenção de duplicação desta carga.
- Referências reais conferidas para 10/10/2026: S10=7.1200 e S500=7.0900.
  Nenhuma despesa de teste criada no banco operacional; despesas anteriores
  preservadas. Conferência visual autenticada no navegador ainda pendente.
- Sem commit, push, merge ou produção.
