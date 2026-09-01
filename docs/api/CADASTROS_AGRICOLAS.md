# Cadastros Agrícolas

A aba **Cadastros agrícolas** centraliza a inclusão e a consulta dos cadastros
usados pelas operações. Ela compõe APIs existentes e não cria entidades ou
fontes de verdade paralelas.

## Locais com finalidades distintas

### Silos e armazéns de grãos

Usam `ArmazemGraos` e são os destinos selecionáveis em Cargas Colhidas. Uma
armazenagem é independente de propriedade, permitindo registrar silos próprios,
cooperativas, cerealistas e outros destinos externos. A propriedade produtora
permanece registrada diretamente na carga e no CAD/PRO.

```text
GET|POST /api/graos/armazens/
GET|PUT|PATCH|DELETE /api/graos/armazens/{id}/
```

O cadastro exige apenas nome e capacidade positiva em quilogramas. A resposta
também informa a ocupação atual. Novas armazenagens não recebem propriedade;
vínculos antigos são mantidos somente para preservar o histórico. A capacidade
não pode ser reduzida abaixo da ocupação.

### Depósitos de insumos

Usam `LocalEstoque` e armazenam lotes de insumos, defensivos, fertilizantes e
sementes. Eles não são destinos de cargas de grãos.

```text
GET|POST /api/estoque/locais/
GET|PUT|PATCH|DELETE /api/estoque/locais/{id}/
```

O cadastro contém nome, propriedade opcional, descrição e status ativo.

## Produtos agrícolas

Produtos reutilizam `ProdutoEstoque`:

```text
GET|POST /api/estoque/produtos/
GET|PUT|PATCH|DELETE /api/estoque/produtos/{id}/
```

Categorias: `insumo`, `herbicida`, `fungicida`, `fertilizante`, `semente` e
`outro`. Unidades: `kg`, `l`, `un`, `sc` e `t`. Fabricante é opcional e estoque
mínimo não pode ser negativo.

## Fornecedores

Fornecedores reutilizam `ParceiroFinanceiro`:

```text
GET|POST /api/financeiro/parceiros/
GET|PUT|PATCH|DELETE /api/financeiro/parceiros/{id}/
```

A inclusão feita pela aba grava `tipo=fornecedor`. A listagem de fornecedores
também apresenta parceiros com `tipo=ambos`. Documento, telefone e e-mail são
opcionais.

## Separação das telas operacionais

- Cargas Colhidas seleciona qualquer armazém de grãos ativo, inclusive externo;
- Estoque mantém o cadastro de lote e as movimentações, mas produto e depósito
  são incluídos na aba central;
- Financeiro mantém categorias e centros de custo, mas fornecedores são
  incluídos na aba central.

Cadastros já vinculados permanecem protegidos. A API responde HTTP 409 quando
uma exclusão física violaria os vínculos existentes; a inativação deve ser
preferida quando houver histórico. Na interface, todos os itens listados possuem
ações **Editar** e **Excluir**; ao receber HTTP 409, a exclusão é convertida em
inativação para preservar cargas, lotes, movimentações e lançamentos anteriores.
# Contratos comerciais

Cadastros agrícolas inclui **Contratos**, com Empresa, Nº do contrato,
Quantidade (kg) e Produto. O formulário aceita `35.000,500` e normaliza para
`35000.500` na API. Permite cadastrar, editar, excluir da seleção e reativar;
exclusão mantém os vínculos históricos. O mesmo contrato é selecionável em
Vendas, sem precisar repetir número e empresa. Consulte `docs/api/VENDAS.md`
para endpoints, idempotência e correções comerciais. Nenhum dado de demonstração
é inserido automaticamente.
