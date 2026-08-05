# API de Grãos

O módulo `graos` mantém o estoque físico de grãos separado do estoque de
insumos. Todo dado é vinculado a uma propriedade por meio do armazém e pode ser
segmentado por lote, cultura, safra e talhão.

Todas as rotas exigem autenticação JWT.

## Entidades

### Armazém

`ArmazemGraos` identifica uma unidade de armazenagem:

- `propriedade`;
- `nome`, único dentro da propriedade;
- `capacidade_kg`, obrigatoriamente positiva;
- `ativo`.

A capacidade não pode ser reduzida abaixo da ocupação atual. Armazéns com lotes
vinculados possuem exclusão protegida.

### Lote

`LoteGraos` identifica grãos homogêneos dentro de um armazém:

- `armazem`;
- `codigo`, único dentro do armazém;
- `cultura` e `safra`;
- `talhao`, opcional e restrito à mesma propriedade do armazém;
- `umidade_percentual` e `impureza_percentual`, opcionais entre 0 e 100;
- `ativo` e `observacoes`.

Após a primeira movimentação, armazém, talhão, cultura e safra não podem ser
alterados. Isso preserva o contexto histórico do saldo.

### Movimentação

`MovimentacaoGraos` é um lançamento imutável de `entrada` ou `saida`:

- `lote`;
- `quantidade_kg`, positiva e com três casas decimais;
- `data_movimento`;
- `referencia_externa` e `observacoes`, opcionais;
- `chave_idempotencia`, opcional e aceita somente na escrita;
- usuário e data de criação, preenchidos pelo backend.

Movimentações podem ser criadas e consultadas, mas não editadas ou excluídas
pela API. Saídas sem saldo, entradas acima da capacidade e movimentações em
lotes ou armazéns inativos são rejeitadas.

A chave de idempotência permite que uma origem futura repita a mesma requisição
sem duplicar o lançamento. Reutilizar a chave com lote, tipo ou quantidade
diferente gera conflito de validação.

## Endpoints

### Armazéns

```text
GET, POST /api/graos/armazens/
GET, PATCH, PUT, DELETE /api/graos/armazens/{id}/
```

Filtros: `propriedade`, `ativo`, `search` e `ordering`.

### Lotes

```text
GET, POST /api/graos/lotes/
GET, PATCH, PUT, DELETE /api/graos/lotes/{id}/
GET /api/graos/lotes/posicao/
GET /api/graos/lotes/resumo/
POST /api/graos/lotes/{id}/transferir/
```

Filtros: `armazem`, `propriedade`, `talhao`, `cultura`, `safra`, `ativo`,
`search` e `ordering`.

A posição retorna entradas, saídas e saldo em quilogramas por lote. O resumo
retorna quantidade de lotes, lotes com saldo e saldo total. Ambos aceitam
`propriedade`, `armazem`, `cultura` e `safra`.

Exemplo de transferência:

```json
{
  "lote_destino": 2,
  "quantidade_kg": "1250.000",
  "data_movimento": "2026-07-30",
  "observacoes": "Transferência operacional",
  "chave_idempotencia": "transferencia-2026-0001"
}
```

A transferência cria uma saída e uma entrada na mesma transação. Os lotes devem
ser diferentes e possuir a mesma cultura e safra. Se saldo ou capacidade forem
insuficientes, nenhum dos dois lançamentos é persistido.

### Movimentações

```text
GET, POST /api/graos/movimentacoes/
GET /api/graos/movimentacoes/{id}/
```

Filtros: `tipo`, `lote`, `armazem`, `propriedade`, `cultura`, `safra`, `search`
e `ordering`.

Exemplo de entrada:

```json
{
  "tipo": "entrada",
  "lote": 1,
  "quantidade_kg": "30000.000",
  "data_movimento": "2026-07-30",
  "referencia_externa": "ROM-100",
  "chave_idempotencia": "origem-futura:rom-100"
}
```

## Integridade e concorrência

O registro de movimentações bloqueia transacionalmente lote e armazém antes de
recalcular saldo e capacidade. Restrições no banco reforçam quantidade e
capacidade positivas, percentuais válidos, unicidade dos cadastros e
idempotência.

A migration inicial é
`backend/apps/graos/migrations/0001_initial.py`. Ela apenas cria as tabelas,
índices, chaves estrangeiras e constraints do módulo; não transforma nem remove
dados existentes.

## Escopo desta entrega

O núcleo de grãos fornece saldo consolidado, ocupação dos armazéns e situação
dos lotes para as regras explicáveis do Assistente Agrícola V1. A integração
não altera o ledger nem classifica a qualidade do produto. Para não mascarar a
ocupação física, saldos negativos não reduzem saldos positivos de outros lotes
e são apresentados pelo Assistente como inconsistência explícita.

O módulo ainda não inclui interface dedicada, regras fiscais ou contábeis.

## Validação

Os testes do módulo cobrem modelos, integridade entre propriedade e talhão,
saldos, capacidade, idempotência, transferências atômicas, imutabilidade,
autenticação, filtros e endpoints:

```powershell
docker compose exec -T -w /app/backend backend `
  python manage.py test apps.graos --settings=config.settings.test
```
