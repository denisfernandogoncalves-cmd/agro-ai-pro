# Cargas Colhidas

O fluxo registra produção recebida manualmente e credita o peso líquido no
ledger de grãos do CAD/PRO, na mesma transação de banco.

## Entidades

- `GrupoColheita`: propriedade, CAD/PRO, cultura, safra, armazenagem padrão e
  regras configuráveis de desconto para umidade, impureza e defeitos;
- `CargaColhida`: data, placa, armazenagem, peso bruto, classificação, peso
  líquido, sacas de 60 kg, regra aplicada, usuário e movimento de estoque.

As cargas são imutáveis. Depois da primeira carga, propriedade, CAD/PRO,
cultura, safra e armazenagem padrão do grupo ficam congelados. Nome e regras de
desconto ainda podem ser ajustados para cargas futuras; cada carga guarda a
fotografia completa da regra usada no cálculo.

Novos grupos exigem CAD/PRO ativo vinculado à propriedade e armazenagem padrão
ativa na mesma propriedade. Uma carga exige grupo, CAD/PRO, vínculo e armazém
ativos. Quando `armazem` não é enviado, a API usa `armazem_padrao` do grupo.
CAD/PRO com saldo físico positivo não pode ser inativado.

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
- `GET|PATCH /api/graos/grupos-colheita/{id}/`
- `POST /api/graos/grupos-colheita/{id}/inativar/`
- `GET|POST /api/graos/cargas-colhidas/`
- `GET /api/graos/cargas-colhidas/{id}/`

Filtros de cargas: `grupo_colheita`, `propriedade`, `cad_pro`, `armazem` e
`data_colheita`. Busca textual abrange placa, local, grupo, propriedade e
CAD/PRO.

Filtros de grupos: `propriedade`, `cad_pro`, `armazem_padrao`, `cultura`,
`safra`, `ativo`, `search` e `ordering`. A resposta inclui
`contexto_congelado`, nomes relacionados e o UUID do CAD/PRO sempre como texto.

## Compatibilidade

As migrations `graos.0005` e `graos.0006` são aditivas. A `0006` inclui a
armazenagem padrão e preenche grupos existentes pela primeira carga ou pelo
primeiro armazém ativo da propriedade, quando disponível. Nenhuma delas remove
dados. O fluxo reutiliza `apps.propriedades`, `apps.cadpro`, `apps.graos` e os
campos já normalizados por `apps.importacoes`.
