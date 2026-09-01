# Vendas de grãos e saldo negativo

O módulo Comercial registra contratos de grãos vinculados obrigatoriamente a
uma `PosicaoSaldoGraos`. O contrato não é uma fonte paralela de estoque: todos
os efeitos usam os serviços públicos transacionais do app `graos`.

## Regras

- Contrato é opcional, tanto no rascunho como na venda com saída. Sem contrato,
  `contrato` fica nulo e `numero_contrato` vazio; não é criado contrato fictício.
  Informe `cliente_nome` ou, na saída, `destino` para identificar o comprador.
  Contratos selecionados continuam fornecendo número e empresa do cadastro.
- rascunho não altera saldo;
- confirmação chama `reservar_saldo` e permite quantidade acima do disponível;
- entrega chama `confirmar_entrega`, reduzindo físico e comprometido;
- venda sem saldo deixa o físico negativo; entradas futuras na mesma posição
  compensam o déficit, sem crédito fictício nem segunda fonte de estoque;
- cancelamento chama `liberar_reserva` apenas para o saldo reservado aberto;
- devolução chama `registrar_devolucao`, recompõe físico e não reabre reserva;
- todos os mutadores exigem `Idempotency-Key` e rejeitam reuso conflitante;
- a posição consolidada exposta no detalhe é a dimensão autoritativa da venda;
- `lote_operacional` e `lote_operacional_codigo` identificam apenas o adaptador
  exigido pelos serviços do ledger e não representam origem física alocada;
- cargas e grupos de colheita não são atribuídos à venda sem uma regra explícita
  de alocação física.

## Propriedade produtora e compatibilidade

O lote operacional deve corresponder a todas as dimensões da posição, incluindo
a propriedade produtora. Duas propriedades que compartilhem CAD/PRO, cultura,
safra, classificação e armazém continuam com posições comerciais independentes.
Não é permitido usar o lote de outra propriedade para reservar ou devolver saldo.

Os campos `propriedade` e `propriedade_nome` da venda e o filtro `propriedade`
referem-se à propriedade da posição oficial, não à proprietária do armazém.
Armazéns externos sem propriedade são compatíveis com esse contrato. Posições
históricas sem propriedade mantêm `null` nesses dois campos; o sistema não
presume uma propriedade a partir do armazém ou dos vínculos atuais do CAD/PRO.

A consulta de posições de saldo expõe também `propriedade_nome`. O formulário
de Vendas apresenta esse nome na opção de posição oficial, diferenciando
posições das duas propriedades mesmo quando as demais dimensões são iguais.

Antes de uma nova movimentação comercial, o serviço confere a coerência entre
lote, posição e reserva. Vínculos incompatíveis retornam HTTP 409 sem modificar
saldos; não são corrigidos silenciosamente. Confirmação e devolução também
conferem a posição retornada pelo ledger dentro da mesma transação, revertendo
o efeito se o destino divergir. Rascunhos continuam canceláveis sem movimento
de estoque, e repetições idempotentes já concluídas mantêm o contrato existente.

Tentar entregar uma venda em rascunho ou sem reserva retorna conflito controlado,
em vez de erro interno por ausência da reserva.

## API autenticada

Base: `/api/comercial/vendas/`

Exemplo de venda sem contrato em `POST /api/comercial/vendas/registrar-saida/`
(enviar também o cabeçalho `Idempotency-Key`):

```json
{"posicao": 1, "destino": "Comprador avulso", "quantidade_kg": "1500.000"}
```

A migration `0007_numero_contrato_opcional` torna o número opcional na validação
do model, sem reescrever vendas existentes. Edição, auditoria, devolução e
cancelamento usam o mesmo fluxo transacional para vendas com ou sem contrato.
Na tela, mantenha **Sem contrato** e preencha Destino. Em rascunhos sem contrato,
preencha Comprador / empresa. O histórico e os relatórios identificam a ausência
do contrato explicitamente. A regra de permitir saldo negativo permanece.

- `GET /` — lista com filtros `search`, `status`, `cad_pro`, `propriedade`,
  `cultura`, `safra`, `classificacao_codigo` e `armazem`;
- `POST /` — cria rascunho;
- `GET /{id}/` — detalha contrato, posição autoritativa, entregas e devoluções;
- `POST /{id}/confirmar/` — cria a reserva oficial;
- `POST /{id}/cancelar/` — libera somente a reserva aberta;
- `POST /{id}/entregar/` — registra entrega parcial ou total;
- `POST /{id}/devolver/` — registra devolução parcial ou total.

Os `POST` exigem o cabeçalho `Idempotency-Key`. Repetição com o mesmo payload
devolve o efeito já realizado; payload diferente com a mesma chave retorna
conflito. Entregas e devoluções concorrentes com a mesma chave e o mesmo
payload são serializadas pela venda e devolvem o único efeito confirmado.

## Cadastro de contratos e correções comerciais (30/08/2026)

`/api/comercial/contratos/`: GET/POST autenticados; detalhe com GET/PATCH/PUT/DELETE.
Campos: `empresa` (160 caracteres), `numero` (80), `quantidade_kg` (decimal positivo,
até três casas), `produto` (80) e `ativo`. Empresa e número formam chave única.
DELETE desativa o cadastro e mantém as vendas vinculadas; PATCH `ativo: true`
reativa. Cadastros novos exigem os quatro campos. Contratos migrados podem estar
sem produto/quantidade até serem completados. O cadastro não reserva estoque.

Na criação da venda, `contrato` referencia esse cadastro. Número e empresa são
copiados pelo servidor, ignorando valores contraditórios enviados pelo cliente.
A API mantém a criação legada com `numero_contrato` e `cliente_nome`. Um contrato
pode ser selecionado em mais de uma venda. A quantidade cadastrada é sugestão,
não uma nova regra de teto agregado; a venda pode deixar o estoque negativo.
Produto é uma informação cadastral; a cultura efetiva do estoque permanece a da
posição oficial escolhida. Alterações do cadastro não reescrevem vendas anteriores.

Correções autenticadas, com `Idempotency-Key`, `versao` atual e `motivo` obrigatório:

- PATCH/DELETE `/api/comercial/vendas/{id}/`;
- PATCH/DELETE `/api/comercial/vendas/{id}/entregas/{movimento_id}/`;
- PATCH/DELETE `/api/comercial/vendas/{id}/devolucoes/{movimento_id}/`.

PATCH da venda aceita contrato, posição, quantidade, datas e observações. PATCH
de movimento exige quantidade e aceita data, referência e observações; entregas
também aceitam destino, placa e notas. DELETE retorna 200 com a venda atualizada.
Edições usam estorno/substituição; exclusões são lógicas e auditadas, sem apagar
o ledger. `alteracoes` informa autor, data e motivo; snapshots completos ficam
armazenados para auditoria. `versao` muda também em confirmar/cancelar/entregar/devolver.

A venda pode ser corrigida ou excluída em qualquer estado, desde que o resultado
respeite os saldos, capacidade e dependências. Excluir venda desfaz suas entregas,
devoluções e reservas; cancelar apenas libera a reserva aberta, como antes.
Excluir uma entrega com devolução dependente ou trocar a posição após entrega
requer corrigir primeiro os movimentos dependentes. Sem saldo/capacidade para
estornar, nenhuma parte da alteração é persistida. Estorno genérico de movimentos
comerciais é bloqueado: usar a venda. Versão desatualizada retorna 409.

Listas normais e relatórios excluem vendas apagadas e movimentos substituídos.
`mostrar_excluidas=true` inclui vendas excluídas na consulta. Os filhos preservados
possuem `cancelado_em`, que consumidores devem filtrar para somar movimentos ativos.

Interface: Cadastros agrícolas → Contratos; Vendas → Nova venda → Contrato/empresa.
Editar/Excluir aparecem nos cartões e movimentos. Exclusões exigem motivo e
confirmação em formulário. Quantidades cadastradas/editadas usam ponto para milhar
e vírgula para decimais; a API continua usando decimais canônicos com ponto.

## Venda com saída em um lançamento (30/08/2026)

Nova venda abre no modo **Venda com saída de grãos**, com Data, Destino, Placa,
Motorista, CAD/PRO, Contrato/empresa (Nº do contrato), Nº nota produtor, Nº nota
empresa e Peso líquido (kg). O seletor **Propriedade / CAD/PRO / Proprietário**
mostra o nome da propriedade, o código fiscal e o proprietário cadastrado.
Cada combinação de propriedade e CAD/PRO é uma opção distinta, inclusive quando
um CAD/PRO atende várias propriedades. Apenas combinações com saldo disponível
positivo aparecem. Proprietário vazio aparece como não informado; produção
histórica sem propriedade permanece identificada separadamente.
As posições disponíveis seguem tanto a propriedade quanto o CAD/PRO escolhidos;
trocar a opção limpa a posição anterior, preservando os outros campos preenchidos.
A posição escolhida continua definindo a cultura, safra e silo. O envio também
verifica se a posição pertence à origem selecionada antes de chamar a API.
**Apenas rascunho** mantém o fluxo anterior sem movimentar estoque. Não há criação
de dados de demonstração ou limpeza automática do banco.

POST `/api/comercial/vendas/registrar-saida/` recebe os campos de criação de venda
e de entrega no mesmo objeto. Exige autenticação e `Idempotency-Key`. O contrato
pode ser informado pelo ID cadastrado. `posicao` define o CAD/PRO; não é permitido
definir um CAD/PRO independente dessa posição. `quantidade_kg` representa o peso
líquido da saída; `data_movimento` é a data da entrega, usando a data do contrato
ou a data atual quando omitida. Na interface, Data alimenta ambas as datas.

O serviço cria a venda, confirma a reserva e registra a entrega em uma única
transação. Retorna 201 com venda entregue e os dados da saída, inclusive sem
saldo suficiente. Uma falha de validação ou entrega reverte também o rascunho
e a reserva. Repetir a chave não
duplica o lançamento; mudar motorista ou outro campo com a mesma chave conflita.

Em criação, informe `posicao` existente **ou** `nova_posicao`, nunca ambos.
`nova_posicao` contém `propriedade`, `cad_pro`, `cultura` (Soja, Milho ou Trigo),
`safra`, `classificacao_codigo` (padrão PADRAO) e `armazem`. Exige CAD/PRO e
armazenagem ativos e vínculo ativo com a propriedade. O serviço reutiliza o lote
compatível ou cria apenas o contexto de estoque, sem movimentação de entrada.
Um erro posterior reverte também esse contexto. Edição utiliza posição existente.

A interface inclui origens com saldo zero/negativo e propriedades vinculadas a
CAD/PRO ativo ainda sem posição. Correções, devoluções, cancelamentos e exclusões
comerciais mantêm auditoria e atomicidade quando há déficit. Reservas genéricas
e transferências continuam exigindo saldo disponível; a permissão interna para
saldo negativo não é exposta como opção da API de grãos.

`motorista` é texto opcional de até 160 caracteres em criação/edição de entregas,
resposta da API, relatório de entregas e snapshots de auditoria. A migration
`0006_entregavendagraos_motorista` mantém entregas antigas sem motorista informado.
Requisições antigas sem motorista conservam seu hash de idempotência. A tabela
exibe Placa / Motorista juntos, sem eliminar sacas, ações ou os demais campos.

A migration 0006 reconhece a coluna PostgreSQL legada `varchar(120)` e amplia
para 160 sem truncar nomes; estruturas inesperadas são recusadas. Em instalações
novas, cria a coluna preenchendo registros antigos com texto vazio. O retorno da
migration preserva a coluna física e seus dados, oferecendo default vazio para
inserções por versões anteriores. Reaplicar é seguro; o retorno não remove nomes
de motoristas. Ciclos de migrations devem ser executados somente em banco de teste.
