# Cargas Colhidas

O fluxo registra produção recebida e credita o peso líquido no ledger oficial
do CAD/PRO, na mesma transação de banco.

## Contexto

- a Propriedade aceita `cad_pro_numero`, normaliza o número e mantém o vínculo
  em `apps.cadpro`, sem duplicar identidade ou ledger;
- o Grupo exige CAD/PRO ativo vinculado à propriedade, cultura e safra;
- armazenagem padrão é legado opcional e não participa mais da criação/edição;
- a Carga exige armazenagem de destino própria, placa e/ou motorista e preserva
  snapshot de propriedades, CAD/PROs, talhões, áreas somadas, safra e cultura em
  `contexto_colheita`.

As cargas e movimentações permanecem imutáveis. O UUID continua sendo a
identidade técnica do CAD/PRO; seu número normalizado é o dado de negócio.

## Descontos

A umidade usa a tabela oficial versionada de 11,5% a 30%, em intervalos exatos
de 0,5. Soja e Milho usam a mesma coluna; Trigo usa sua coluna própria. Valor
fora da faixa ou entre pontos é rejeitado, sem interpolação.

Impureza e Quebrados usam o excesso sobre a tolerância configurada no Grupo do
grão. PH usa o déficit abaixo do PH mínimo configurado. O cálculo usa `Decimal`,
e a regra completa fica em `regra_desconto_aplicada`.

```text
desconto kg = peso bruto × desconto total / 100
peso líquido = peso bruto - desconto kg
sacas = peso líquido / 60
```

## APIs

- `GET|POST /api/graos/grupos-colheita/`
- `GET|PATCH /api/graos/grupos-colheita/{id}/`
- `POST /api/graos/grupos-colheita/{id}/inativar/`
- `GET|POST /api/graos/cargas-colhidas/`
- `GET /api/graos/cargas-colhidas/{id}/`

Filtros de grupos: `propriedade`, `cad_pro`, `cultura`, `safra`, `ativo`,
`search` e `ordering`. Busca de cargas inclui placa e motorista.

## Banco

`graos.0008` é aditiva: preserva a armazenagem padrão histórica, torna seu uso
opcional, adiciona motorista, snapshot do contexto da colheita e regras de PH.
Nenhuma coluna ou dado histórico é removido.
