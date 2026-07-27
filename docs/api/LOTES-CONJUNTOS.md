# API — Lotes Conjuntos de Produção

Todos os endpoints exigem JWT e aplicam as permissões multiusuário da PR #16 sobre
todas as propriedades participantes. Um lote só é visível quando o usuário possui
acesso a todas as propriedades relacionadas.

## Criar lote em rascunho

```http
POST /api/producao/lotes-conjuntos/
Content-Type: application/json
```

Exemplo resumido:

```json
{
  "descricao": "Colheita não separada",
  "cultura": 1,
  "safra": 3,
  "data_inicio_colheita": "2026-07-20",
  "local_armazenagem": 2,
  "modo_rateio": "sem_rateio",
  "participantes": [
    {
      "propriedade": 10,
      "cadpro": 4,
      "area_cadastrada_ha": "40.0000",
      "area_colhida_ha": "30.0000",
      "talhoes": [
        {
          "talhao": 21,
          "area_cadastrada_ha": "40.0000",
          "area_colhida_ha": "30.0000"
        }
      ]
    },
    {
      "propriedade": 11,
      "cadpro": 5,
      "area_cadastrada_ha": "30.0000",
      "area_colhida_ha": "20.0000",
      "talhoes": []
    }
  ]
}
```

Regras:

- pelo menos duas propriedades distintas;
- todas as propriedades devem estar autorizadas;
- CAD/PRO deve pertencer à respectiva propriedade e estar autorizado;
- área acima da disponível exige administrador e justificativa;
- o modo padrão é `sem_rateio`;
- os totais são calculados no backend.

## Buscar e filtrar

```http
GET /api/producao/lotes-conjuntos/?search=LC-2026
GET /api/producao/lotes-conjuntos/?propriedade=10
GET /api/producao/lotes-conjuntos/?municipio=Ivaiporã
GET /api/producao/lotes-conjuntos/?produtor=Silva
GET /api/producao/lotes-conjuntos/?cadpro=4
GET /api/producao/lotes-conjuntos/?cultura=1&safra=3&status=confirmado
GET /api/producao/lotes-conjuntos/?data_inicio=2026-07-01&data_fim=2026-07-31
```

## Cargas

```http
POST /api/producao/cargas-lotes-conjuntos/
```

Registra motorista, cavalo, carreta, placas legadas, transportadora, origem,
destino, pesos, classificação, romaneio, balança, nota fiscal e local.

A inclusão ou alteração recalcula os totais e as médias ponderadas do lote. Cargas
não podem ser alteradas após a confirmação.

## Conferência e confirmação

```http
POST /api/producao/lotes-conjuntos/{id}/colocar-em-conferencia/
POST /api/producao/lotes-conjuntos/{id}/confirmar/
```

A confirmação:

- exige duas ou mais propriedades;
- exige ao menos uma carga;
- exige área colhida e peso líquido positivos;
- cria entrada no saldo conjunto;
- registra usuário, data, totais e propriedades na auditoria;
- bloqueia edição direta posterior.

## Rateio pela área

```http
POST /api/producao/lotes-conjuntos/{id}/ratear-area/
```

Distribui proporcionalmente à área colhida. O ajuste de arredondamento é aplicado na
última parcela, preservando o total exato. Todos os participantes precisam possuir
CAD/PRO confiável e autorizado.

## Rateio manual

```http
POST /api/producao/lotes-conjuntos/{id}/ratear-manual/
Content-Type: application/json
```

```json
{
  "justificativa": "Divisão conferida pelas pesagens complementares",
  "distribuir_todo_saldo": true,
  "itens": [
    {
      "participante": 101,
      "cadpro": 4,
      "quantidade": "12",
      "unidade": "toneladas"
    },
    {
      "participante": 102,
      "cadpro": 5,
      "quantidade": "8000",
      "unidade": "kg"
    }
  ]
}
```

Unidades aceitas: `kg`, `toneladas` e `sacas`. A justificativa é obrigatória. Quando
`distribuir_todo_saldo` for verdadeiro, a soma deve ser exatamente igual ao saldo
conjunto.

## Transferência de local

```http
POST /api/producao/lotes-conjuntos/{id}/transferir/
```

```json
{
  "local_origem": 2,
  "local_destino": 3,
  "quantidade_kg": "5000.000"
}
```

A operação bloqueia linhas de saldo, impede saldo negativo e registra saldos anterior
e posterior.

## Ajuste administrativo

```http
POST /api/producao/lotes-conjuntos/{id}/ajustar-saldo/
```

```json
{
  "local": 2,
  "quantidade_kg": "-20.000",
  "justificativa": "Correção de aferição documentada"
}
```

Somente administrador. A justificativa é obrigatória.

## Saídas

```http
POST /api/producao/saidas-lotes-conjuntos/
POST /api/producao/saidas-lotes-conjuntos/{id}/confirmar/
POST /api/producao/saidas-lotes-conjuntos/{id}/estornar/
```

A confirmação baixa exclusivamente o saldo conjunto do local informado. O estorno é
administrativo, exige motivo e restaura o saldo original.

Saídas de saldo já distribuído por propriedade ou CAD/PRO continuam utilizando o
fluxo individual existente de embarques e `SaldoGraos`.

## Transporte

```http
GET /api/producao/lotes-conjuntos/{id}/resumo-transportes/
```

Retorna quantidade de cargas, peso total, peso médio e consolidações por motorista,
veículo e transportadora.

## Saldos e auditoria operacional

```http
GET /api/producao/saldos-lotes-conjuntos/?lote={id}
GET /api/producao/movimentacoes-lotes-conjuntos/?lote={id}
```

Movimentações retornam quantidade, origem, destino, usuário, referência e saldos
anteriores/posteriores.

## Relatórios

```http
GET /api/producao/relatorios-lotes-conjuntos/?formato=csv
GET /api/producao/relatorios-lotes-conjuntos/?formato=xlsx
GET /api/producao/relatorios-lotes-conjuntos/?formato=pdf
```

Aceita filtros de cultura, safra, status, propriedade e período. Os arquivos são
gerados localmente, sem serviço externo.
