# API de Estoque

Todos os endpoints exigem autenticação JWT e usam o prefixo `/api/estoque/`.

## Cadastros

- `GET|POST /produtos/`
- `GET|PUT|PATCH|DELETE /produtos/{id}/`
- `GET|POST /locais/`
- `GET|PUT|PATCH|DELETE /locais/{id}/`
- `GET|POST /lotes/`
- `GET|PUT|PATCH|DELETE /lotes/{id}/`

Produtos aceitam as categorias `insumo`, `herbicida`, `fungicida`,
`fertilizante`, `semente` e `outro`. As unidades aceitas são `kg`, `l`, `un`,
`sc` e `t`.

Um lote pertence a um produto agrícola do catálogo central, possui código e
pode informar validade. O novo formulário usa `fornecedor`, vinculado a
`financeiro.ParceiroFinanceiro` ativo do tipo fornecedor ou ambos. O campo
`local` tornou-se opcional; os depósitos dos lotes anteriores são preservados.
A API mantém compatibilidade com lotes por local, mas exige fornecedor quando
não houver local. Produtos inativos não podem ser selecionados em novos lotes.
Sem local, produto + fornecedor + código são únicos na API e no banco.
Listas e posições retornam também o nome do fornecedor. Cadastros vinculados a lotes ou movimentos não podem ser
excluídos; a API responde HTTP 409.

## Movimentações

- `GET|POST /movimentacoes/`
- `GET /movimentacoes/{id}/`

Campos principais:

- `tipo`: `entrada` ou `saida`;
- `lote` e `quantidade`: obrigatórios;
- `custo_unitario`: obrigatório para entrada;
- `data_movimento`;
- `documento_fiscal`: opcional;
- `propriedade`, `safra` e `observacoes`: opcionais.

A API rejeita saídas superiores ao saldo do lote. Movimentações não aceitam
edição nem exclusão e retornam o usuário e a data responsáveis pelo registro.

Filtros disponíveis: `tipo`, `lote`, `produto`, `local`, `propriedade`, `safra`
e busca por produto, lote, documento ou observação. A ordenação aceita data,
quantidade, custo e tipo.

## Posição e alertas

- `GET /lotes/posicao/`
- `GET /lotes/resumo/`

A posição retorna saldo por lote, unidade, localização, validade e indicadores
de vencimento e estoque mínimo. O resumo contabiliza produtos ativos, lotes com
saldo, lotes vencidos, lotes próximos do vencimento e itens abaixo do mínimo.

## Cadastro na interface

O botão **Novo lote**, junto ao seletor da movimentação, abre o cadastro e
posiciona o foco no produto. Após salvar, o lote é selecionado automaticamente,
preservando os demais campos da movimentação. O cadastro não registra entrada
nem saída: o usuário ainda precisa completar e enviar a movimentação.
Produto agrícola e fornecedor devem existir em **Cadastros agrícolas**.
O botão **Atualizar cadastros** recarrega essas opções; abrir **Novo lote**
também atualiza o catálogo. Apenas registros ativos aparecem nos seletores.

Migration: `estoque.0002_loteestoque_fornecedor_alter_loteestoque_local_and_more`.
Ela adiciona o fornecedor opcional e permite local nulo, sem converter depósitos
em fornecedores nem alterar vínculos históricos. Lotes sem depósito não entram
nos relatórios filtrados por propriedade do depósito.

A inclusão e a listagem de depósitos de insumos e produtos agrícolas ficam
centralizadas na aba **Cadastros agrícolas**, reutilizando estes mesmos
endpoints. A tela **Estoque** mantém o cadastro de lotes e a operação de
movimentações, sem formulários duplicados de produto ou local.

Veja [Cadastros agrícolas](CADASTROS_AGRICOLAS.md).
# Compras em embalagens — 14/09/2026

Atualização: **Safra** foi acrescentada após Cultura, no formulário e na tabela
(agora 13 campos). Exemplo: `2026`. A API recebe e retorna `safra`, texto opcional
de até 20 caracteres, armazenado no campo já existente da movimentação.
A busca também considera safra. Compras antigas permanecem sem safra informada,
e reenvios antigos sem o campo mantêm a compatibilidade. Não exige migration.

O formulário principal e a tabela de compras exibem, nesta ordem:
Data da compra, Produto, Cultura, QTD, PCT, L / KG, Fornecedor,
Custo unitário, Data de vencimento, QT em litros / kg, Valor / L ou kg,
Valor total. Produtor foi excluído por orientação expressa do Product Owner.
Data de vencimento é o pagamento da compra, e não a validade do produto.

## Cálculos e compatibilidade

- QTD representa a quantidade de embalagens; PCT identifica seu tipo (GL, BAG, BD, PCT etc.).
- L / KG é o conteúdo de cada embalagem na unidade cadastrada do produto.
- Quantidade total = QTD × conteúdo da embalagem.
- Custo unitário da tabela é o custo por embalagem; valor por L/kg = custo da embalagem ÷ conteúdo.
- Valor total = QTD × custo da embalagem, arredondado para centavos diretamente, sem usar o valor por L/kg já arredondado.
- Produtos da nova compra devem estar ativos e usar `l` ou `kg`. Produtos de outras unidades continuam disponíveis nas movimentações anteriores.
- A entrada no ledger armazena quantidade na unidade base (três casas) e custo por unidade base (quatro casas). Compra preserva quantidade, conteúdo e custo das embalagens e valor total exato.
- Cada compra cria um lote de rastreabilidade e uma única entrada, na mesma transação. A validade desse novo lote fica não informada; o vencimento de pagamento é armazenado na compra.
- Não há geração automática de conta a pagar. Cultura e vencimento podem ficar não informados. Custo deve ser informado (zero é aceito).
- Movimentos antigos permanecem em Outras movimentações, saldos e rastreabilidade; não recebem dados de embalagem inventados nem são convertidos em compras automaticamente.

## API autenticada

`GET /api/estoque/compras/` lista compras, com busca `search` por produto,
cultura ou fornecedor. Ordenação por `movimento__data_movimento`,
`data_vencimento` ou `valor_total`. `GET /api/estoque/compras/{id}/` consulta
uma compra. Atualização e exclusão não são expostas, preservando o ledger.

`POST /api/estoque/compras/` recebe:

```json
{
  "id": "73ea2829-cb6d-4185-a546-52fcb9ed2026",
  "data_compra": "2026-09-14",
  "produto": 1,
  "cultura": "Soja",
  "quantidade_embalagens": "143",
  "embalagem": "GL",
  "conteudo_embalagem": "5",
  "fornecedor": 1,
  "custo_embalagem": "370.00",
  "data_vencimento": "2027-07-02"
}
```

IDs de produto e fornecedor devem existir; o fornecedor deve estar ativo e ser
fornecedor ou ambos. UUID identifica a solicitação para impedir duplicação.
Retorno 201 na primeira gravação, 200 ao repetir a mesma chave e dados, 409 ao
repetir a chave com conteúdo diferente; validação retorna 400 e falta de
autenticação retorna 401. Resposta inclui `quantidade_total`,
`valor_por_unidade`, `valor_total`, nomes do produto/fornecedor e movimento.
No exemplo: 715 litros, R$ 74/litro e R$ 52.910,00.

Migration aditiva `estoque.0003_compraestoque`; testes em
`test_compras.py` e `test_compras_calculos.py`.
