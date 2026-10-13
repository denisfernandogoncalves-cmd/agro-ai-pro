# Importação local das planilhas de insumos — 09/10/2026

## Resultado aplicado

No banco local servido pelo backend Docker, foram criadas 72 propriedades,
24 CAD/PROs, 61 vínculos CAD/PRO–propriedade, 11 fornecedores e 59 produtos
cuja unidade litro/kg está explícita nas fontes. Cadastros existentes foram
reutilizados; áreas e códigos divergentes não foram sobrescritos.

As três fontes foram preservadas integralmente no módulo Importações:

| Lote | Fonte | Linhas com conteúdo, incluindo cabeçalhos e resumos |
| --- | --- | --- |
| 7 | ESTOQUE .xlsx | 1.803 |
| 8 | CVALE.xlsx | 112 |
| 9 | AGRO PRODUZ.xlsx | 116 |

As linhas guardam valores originais, fórmulas, coordenadas de células e,
para compras/retiradas, campos identificados pelo cabeçalho. Sete erros de
fórmula originais continuam visíveis. A validação cadastral não significa
que o histórico está conciliado para movimentação de estoque.

O complemento autorizado da coluna G da C.Vale preencheu `bp_cvale` em
60 propriedades. Seis BPs continuam no histórico porque suas propriedades
ainda não têm associação inequívoca; nenhum BP divergente foi substituído.

## Regras confirmadas pelo Product Owner

- Compra permanece no fornecedor; retirada significa entrega à fazenda.
- Compras antigas ficam como histórico, sem criar dívidas pendentes.
- Um alqueire paulista corresponde a 2,42 hectares.
- A abreviação NEI corresponde a Claudinei Silvestre.
- Município da Electra: Jardim Alegre/PR.

Não foram gerados lançamentos financeiros, compras operacionais, saídas de
consumo ou saldos físicos com base no histórico. A movimentação de estoque
preexistente foi preservada. Registros dos fornecedores não foram confundidos
com estoque recebido nas fazendas.

## Localização e pendências

Coordenadas foram convertidas de graus/minutos/segundos para graus decimais
e cruzadas localmente com a malha simplificada municipal do IBGE, qualidade
máxima da API v3. O resultado informa o município do ponto fornecido,
sem comprovar os limites completos da propriedade ou seu município fiscal.

Nomes distintos entre fontes só foram reunidos quando área, produtor,
CAD/PRO e ponto coincidiam integralmente, com uma única linha por fonte.
Não foram presumidas equivalências adicionais. As 121 ocorrências de revisão
cadastral incluem unidades não explícitas, áreas/códigos divergentes e
propriedades incompletas. Elas estão nos metadados dos lotes e no relatório
privado; não representam 121 propriedades distintas.

## Preservação e execução

Backup do diretório principal: `backups/visual-20261009-132537`.
Backup do código ativo, banco e uploads: `backups/visual-20261009-132539`.
Backup antes do complemento BP: `backups/visual-20261009-134053`.
ZIPs, dumps e hashes foram verificados pelos scripts existentes.

Fontes privadas e relatórios ficam em
`backups/importacao-insumos-20261009-131331`, ignorado pelo Git. Os hashes das
planilhas atuais foram comparados aos das cópias antes da carga.

Importador: `scripts/importar_insumos_historico.py`. Recebe o dicionário
`INSUMOS_PAYLOAD` no shell Django; `INSUMOS_APLICAR=False` ensaia com rollback,
`True` grava. Usa transação, lock de importação no PostgreSQL e SHA-256 único
por fonte. Um reenvio das mesmas fontes não criou novos dados.

Complemento BP: `scripts/completar_bp_cvale_importado.py`, com a mesma opção
de ensaio e aplicação. Usa o vínculo auditado da linha para preencher apenas
BP vazio ou idêntico ao da fonte. Não altera outros campos da propriedade.

## Alteração técnica e verificações

Adicionado o valor `historico` às opções de tipo/status do módulo existente
Importações. Migration `importacoes.0004_historico_insumos` aplicada no código
ativo. A cópia principal possui `0003_historico_insumos`, com dependência
ajustada à sua sequência de migrations. Histórico não é elegível para
confirmação como movimentação de grãos.

- Ensaio completo com rollback aprovado; refinamento da deduplicação ensaiado.
- 36 testes de importações e proteção do histórico aprovados no Docker,
  usando `--settings=config.settings.test` em SQLite isolado.
- Dois testes da proteção do histórico também aprovados na cópia principal.
- `manage.py check` e `makemigrations --check --dry-run` do código ativo aprovados.
- Consulta autenticada/paginada dos lotes e linhas: HTTP 200, 2.031 linhas.
- Reenvio não criou cadastros nem lotes; nenhuma dívida criada, saldo preservado.
- Sintaxe dos arquivos novos e revisão de diff aprovadas.

A validação global de migrations da cópia principal encontrou uma dependência
preexistente não reconhecida `graos.0005` → `cadpro.0001`; essa cópia não é o
diretório montado pelo backend ativo. Nenhuma correção fora do escopo foi feita.
A tentativa de ajustar textos da tela encontrou bloqueio de escrita do arquivo;
o frontend foi preservado. A tela existente consulta os históricos normalmente,
mas seu texto genérico continua descrevendo o envio de planilhas de grãos.

Não houve commit, push, merge ou publicação em produção. A conciliação
operacional de estoque e os cadastros pendentes não estão concluídos.
