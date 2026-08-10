# Cargas Colhidas

O fluxo registra produção recebida manualmente e credita o peso líquido no
ledger de grãos do CAD/PRO, na mesma transação de banco.

## Entidades

- `GrupoColheita`: propriedade, CAD/PRO, cultura, safra e regras configuráveis
  de desconto para umidade, impureza e defeitos;
- `CargaColhida`: data, placa, armazenagem, peso bruto, classificação, peso
  líquido, sacas de 60 kg, regra aplicada, usuário e movimento de estoque.

As cargas são imutáveis. O grupo pode ser atualizado para cargas futuras, mas
cada carga guarda a fotografia completa da regra usada no cálculo.

## Cálculo

```text
excesso = máximo(medição - tolerância, 0)
desconto do indicador (%) = excesso × desconto por ponto
desconto kg = peso bruto × desconto total / 100
peso líquido = peso bruto - desconto kg
sacas = peso líquido / 60
```

Desconto total igual ou superior a 100% é rejeitado.

## Duplicidade e rastreabilidade

A chave de duplicidade usa grupo, data, placa normalizada e peso bruto. Uma
segunda requisição com a mesma combinação retorna HTTP `409` e não duplica o
saldo. A carga referencia o lote automático e a movimentação imutável do
ledger, além de registrar usuário e data/hora de criação.

## APIs autenticadas

- `GET|POST /api/graos/grupos-colheita/`
- `GET|PATCH|DELETE /api/graos/grupos-colheita/{id}/`
- `GET|POST /api/graos/cargas-colhidas/`
- `GET /api/graos/cargas-colhidas/{id}/`

Filtros de cargas: `grupo_colheita`, `propriedade`, `cad_pro`, `armazem` e
`data_colheita`. Busca textual abrange placa, local, grupo, propriedade e
CAD/PRO.

## Compatibilidade

A migration `graos.0005` é aditiva. Ela cria tabelas, índices e restrições sem
alterar ou remover dados anteriores. O fluxo reutiliza `apps.propriedades`,
`apps.cadpro`, `apps.graos` e os campos já normalizados por `apps.importacoes`.
