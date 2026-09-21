# API Financeira

Todas as rotas exigem autenticação JWT.

## Leitor USB de códigos de pagamento

`POST /api/financeiro/lancamentos/ler-codigo/` recebe `{"codigo": "..."}`.
Aceita código de barras de 44 dígitos e linhas digitáveis de 47 (cobrança)
ou 48 (arrecadação), com espaços, pontos e hífens. Valida dígitos gerais e
dos blocos pelos módulos 10/11 antes de extrair os dados. Entrada inválida
retorna 400; a prévia exige login e não salva nem liquida lançamentos.

Retorna código normalizado, tipo, código do banco ou segmento/identificador
do emissor, valor em reais quando disponível, possíveis vencimentos, avisos
e até dez lançamentos existentes com o mesmo código. O aviso de repetição
não é uma trava de unicidade: o usuário precisa conferir antes de salvar.

Boletos têm duas possibilidades de vencimento por causa do reinício do fator
em 22/02/2025. A interface exige escolher a data impressa antes de aplicar.
Fatores abaixo de 1000 e contas de arrecadação exigem informar a data
manualmente. Datas aparentes no campo livre não são presumidas como vencimento.
Valores de referência (identificadores 7/9) não são convertidos para reais;
valor zero é tratado como valor não informado. Títulos cujo valor ocupa também
o campo de vencimento precisam de conferência e ajuste manual.

Em Financeiro, clicar em **Posicionar leitor**, usar o leitor USB em modo
teclado e pressionar Enter ou **Extrair dados**. Depois de conferir a prévia,
usar **Aplicar ao lançamento**, completar os campos e **Salvar lançamento**.
O Enter do leitor pertence ao formulário de leitura e não salva o financeiro.
Aplicar substitui valor e vencimento; campos não extraíveis ficam vazios para
preenchimento. Descrição, fornecedor, categoria e contexto agrícola são preservados.

`codigo_barras` é opcional nos lançamentos, normalizado e validado também
ao salvar pela API. A migration aditiva `financeiro.0002_codigo_barras` adiciona
o campo vazio aos registros anteriores. O código fica disponível para consulta
na listagem. Não há pagamento, consulta bancária, DDA, OCR, Pix ou captura de
imagem nesta entrega. Nome e CPF/CNPJ completo do fornecedor não são inferidos.

Referências técnicas consultadas em 10/09/2026:

- [Manual de boletos do Banco do Brasil](https://www.bb.com.br/docs/pub/emp/empl/dwn/Doc5175Bloqueto.pdf).
- [FEBRABAN: leiaute de arrecadação versão 8](https://cmsarquivos.febraban.org.br/Arquivos/documentos/PDF/Layout%20-%20C%C3%B3digo%20de%20Barras%20-%20Vers%C3%A3o%208%20-%2011_05_2026.pdf).

## Cadastros auxiliares

- `/api/financeiro/categorias/`
- `/api/financeiro/parceiros/`
- `/api/financeiro/centros-custo/`

As três coleções oferecem CRUD, busca e ordenação. Categorias em uso,
parceiros vinculados e centros com lançamentos não podem ser excluídos.

## Lançamentos

- `GET|POST /api/financeiro/lancamentos/`
- `GET|PUT|PATCH|DELETE /api/financeiro/lancamentos/{id}/`
- `POST /api/financeiro/lancamentos/{id}/liquidar/`
- `POST /api/financeiro/lancamentos/{id}/cancelar/`
- `GET /api/financeiro/lancamentos/resumo/`

Filtros:

- `tipo`: `pagar` ou `receber`;
- `status`: `pendente`, `liquidado` ou `cancelado`;
- `categoria`, `parceiro`, `centro_custo` e `propriedade`: IDs;
- `safra`;
- `vencimento_inicio` e `vencimento_fim`;
- `search` e `ordering`.

Para liquidar:

```json
{
  "data_liquidacao": "2026-07-25",
  "valor_liquidado": "1500.00"
}
```

O resumo retorna valores a pagar, a receber, saldos previsto e realizado,
entradas, saídas, total atrasado e quantidade pendente.

## Cadastro de fornecedores na interface

A inclusão e a listagem de fornecedores ficam centralizadas na aba
**Cadastros agrícolas**, reutilizando `/api/financeiro/parceiros/`. A criação
usa `tipo=fornecedor`; a listagem também apresenta parceiros `tipo=ambos`. A
tela **Financeiro** mantém categorias, centros de custo e a operação financeira,
sem formulário duplicado de parceiro.

Veja [Cadastros agrícolas](CADASTROS_AGRICOLAS.md).


## Leitura ampliada em 11/09/2026

A resposta de ler-codigo também fornece linha_digitavel,
linha_digitavel_formatada, formato_entrada, descricao_sugerida e detalhes
(pares campo/valor). A interface mostra moeda ou referência, fator de
vencimento, identificador do emissor e campo livre integral. A descrição
sugerida somente preenche uma descrição vazia. Raiz de CNPJ não é exibida
como CNPJ completo. Agência, conta, carteira, nosso número, beneficiário e
situação do pagamento não são inferidos sem leiaute específico homologado.
O código já persistido permite repetir a extração. Nenhuma consulta externa
é feita. Conferir valor e vencimento antes de salvar.

Fontes conferidas: manual de boletos do Banco do Brasil e leiaute FEBRABAN
versão 8, nos links da seção de referências deste documento.

## Identificação local pelo leitor em 12/09/2026

`ler-codigo` retorna também `banco_nome` (string ou null), obtido pelo código
de três dígitos no catálogo público STR do Banco Central. O catálogo local
`backend/apps/financeiro/bancos_str.json` contém fonte, data da consulta e
licença ODbL. Não há envio do boleto nem consulta externa durante a leitura.
Códigos ausentes permanecem válidos conforme os dígitos, com nome indisponível;
arrecadação não recebe nome de banco por interpretação dos primeiros dígitos.

Para Itaú (341), as carteiras 104, 108, 109, 112, 115, 121, 147, 150, 180,
188 e 191 permitem detalhar agência, conta com dígito, carteira e nosso número
com dígito. A extração exige os zeros finais e os dígitos internos coerentes
com o manual; 150 usa a regra específica de nosso número. Outras carteiras
ou formatos preservam o campo livre sem atribuir nomes incorretos aos dados.
Isso não constitui confirmação da titularidade ou autenticidade do boleto.

O nome do banco compõe a descrição sugerida apenas quando vazia. O resumo dos
campos extraídos permanece no formulário após aplicar; desvincular o código
ou salvar o lançamento limpa o resumo. Não houve alteração de schema: o código
persistido permite repetir a leitura. Dados manuais de parceiro e categoria
são preservados. A aplicação e o salvamento continuam explícitos.

Somente o leitor não identifica nome/CPF/CNPJ completo do recebedor, juros,
descontos ou situação de pagamento. O nome do banco não identifica o recebedor.
A ambiguidade do fator de vencimento continua exigindo conferência.

Fontes: [catálogo STR do BCB](https://dadosabertos.bcb.gov.br/en/dataset/lista-de-participantes-do-str)
e [manual Itaú CNAB 400](https://download.itau.com.br/bankline/layout_cobranca_400bytes_cnab_itau.pdf),
seção 7.3.2 e anexo 4. Validações em
`docs/decisoes/2026-09-12-leitor-bancos.md`.

## Cadastro de um boleto da compra — revisão de 14/09/2026

A orientação final de 12/09 substitui a divisão automática no formulário:
cada salvamento registra somente um boleto, preservando valor, vencimento e
código lido. Os campos **Número deste boleto** e **Total de boletos da compra**
exibem, por exemplo, **1 de 4**, também na lista de lançamentos.

`POST /api/financeiro/lancamentos/registrar-boleto/` exige autenticação e recebe
`idempotency_key` (UUID), `tipo`, `descricao`, `recebedor_nome`, `valor`,
`parcela_numero`, `total_boletos`, `data_emissao`, `data_vencimento`,
`observacoes` e `codigo_barras`. Número e total são inteiros de 1 a 9999;
o número não pode superar o total. Valor mínimo: R$ 0,01.

Retorna 201 com `boleto` e `replay=false`. Repetição com mesma chave e dados
retorna 200 e `replay=true`, sem duplicação; conteúdo diferente retorna 409.
Não calcula valores ou vencimentos dos demais boletos da compra.

Migration aditiva: `financeiro.0004_lancamentofinanceiro_total_boletos`.
O formulário e o leitor usam posicionamento estático no Financeiro para
evitar sobreposição durante a rolagem.

## API anterior de parcelamento — histórico de 12/09/2026

O comportamento abaixo foi substituído no formulário pela orientação acima.
A API anterior permanece disponível por compatibilidade e não é chamada
pelo cadastro atual de boletos.

O formulário substitui categoria, parceiro, centro de custo, propriedade e
safra por **Quem vai receber** e **Quantidade de boletos**. O recebedor pode ser
digitado ou escolhido nas sugestões de cadastros ativos; seu nome é salvo em
`recebedor_nome`, sem criar parceiro implicitamente. Vínculos antigos continuam
disponíveis na API. Categoria passa a ser opcional; relatórios aceitam ausência.

`POST /api/financeiro/lancamentos/parcelar/` exige autenticação e recebe:

```json
{
  "idempotency_key": "611e0e72-90ac-47de-b04a-017876d8628c",
  "tipo": "pagar",
  "descricao": "Compra de insumos",
  "recebedor_nome": "Fornecedor exemplo",
  "valor_total": "100.00",
  "quantidade": 3,
  "data_emissao": "2026-09-12",
  "primeiro_vencimento": "2026-10-31",
  "observacoes": "",
  "codigo_barras": ""
}
```

Quantidade de 1 a 120, mínimo de R$ 0,01 por parcela. Total calculado em
centavos: o resto vai para as primeiras parcelas. Vencimentos mensais usam
sempre o dia original, limitado ao último dia de cada mês. A prévia mostra
valores e datas antes de salvar. Não há emissão de títulos bancários.

Resposta 201: `id`, `replay=false`, `parcelas` (lançamentos com valor, vencimento,
recebedor, `parcelamento` e `parcela_numero`). A mesma chave UUID e conteúdo
retornam 200, `replay=true`, sem duplicação. Conteúdo diferente com a mesma chave
retorna 409. Validação inválida retorna 400; a gravação de todas as parcelas e
do grupo ocorre em uma transação, revertida em falha intermediária.

Um único lançamento pode preservar o código lido. Ao dividir em várias parcelas,
a interface usa o valor como total e não replica o código. A API rejeita código
preenchido quando quantidade > 1: um boleto existente não representa cada uma
das novas parcelas. Nome do recebedor não é extraído do código.

Migration `financeiro.0003_parcelamentofinanceiro_and_more`, aplicada localmente.
Evidências em `docs/decisoes/2026-09-12-parcelas-financeiro.md`.
