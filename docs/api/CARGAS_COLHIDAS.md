# Cargas Colhidas

O fluxo registra diretamente a produção recebida por propriedade, CAD/PRO,
cultura, safra e armazenagem. O peso líquido calculado é creditado no ledger
oficial do CAD/PRO na mesma transação de banco. Uma carga pode reunir várias
propriedades: suas áreas declaradas são somadas e o peso líquido é rateado
proporcionalmente, com uma parcela auditável no CAD/PRO de cada propriedade.

Grupo de Colheita não participa mais da operação, da API ou da interface. A
entidade e seus registros permanecem no banco apenas como legado protegido para
preservar cargas históricas; novas cargas são criadas sem esse vínculo.

## Contexto direto e integridade

Cada carga possui como dimensões próprias e obrigatórias:

- `propriedade`;
- `cad_pro`;
- `cultura`: `Soja`, `Milho` ou `Trigo`;
- `safra`;
- `armazem`.

O backend valida que o CAD/PRO principal está ativo e possui vínculo ativo com a
propriedade principal. `propriedades_selecionadas` aceita uma ou mais
propriedades. A interface apresenta apenas essa seleção múltipla e solicita o
CAD/PRO dentro de cada propriedade marcada, sem um seletor singular redundante.
`cadpros_por_propriedade` registra essas escolhas e cada CAD/PRO deve possuir
vínculo ativo com sua respectiva propriedade. Os IDs
enviados em `talhoes_selecionados` devem pertencer a uma das propriedades
selecionadas. A armazenagem deve estar ativa e é um
destino independente e pode representar silo próprio ou externo. O lote de grãos é
determinado pelo servidor e mantém coerência com CAD/PRO, cultura, safra,
classificação e armazenagem.

Placa e motorista são opcionais isoladamente, mas ao menos um deles deve ser
informado. A placa é normalizada e deve conter sete letras e números.

`contexto_colheita` congela o contexto produtivo usado no registro, incluindo
propriedades, CAD/PROs, talhões, áreas e rateio de produção. Cada parcela também
é persistida em `RateioCargaColhida` e possui lote e movimentação próprios, para
que saldo, correção e cancelamento sejam aplicados a todos os CAD/PROs. O
fingerprint de duplicidade usa as dimensões diretas, data, veículo e peso bruto;
não depende de Grupo de Colheita.

O UUID continua sendo a identidade técnica do CAD/PRO, enquanto seu código
normalizado é o identificador de negócio exibido ao usuário.

## Tabela oficial de desconto de umidade

O cálculo usa `Decimal` e a tabela versionada `2026-08-20`. Somente valores
entre 11,5% e 30%, em intervalos exatos de 0,5 ponto percentual, são aceitos.
Não existe interpolação silenciosa. Soja e Milho compartilham uma coluna; Trigo
usa sua própria coluna.

| Umidade (%) | Soja/Milho (%) | Trigo (%) |
| ---: | ---: | ---: |
| 11,5 | 0 | 0 |
| 12,0 | 0 | 0 |
| 12,5 | 0 | 0 |
| 13,0 | 0 | 0 |
| 13,5 | 0 | 1 |
| 14,0 | 0 | 1,75 |
| 14,5 | 1 | 2,5 |
| 15,0 | 1,75 | 3,25 |
| 15,5 | 2,5 | 4 |
| 16,0 | 3,25 | 4,75 |
| 16,5 | 4 | 5,5 |
| 17,0 | 4,75 | 6,25 |
| 17,5 | 5,5 | 7 |
| 18,0 | 6,25 | 7,75 |
| 18,5 | 7 | 8,5 |
| 19,0 | 7,75 | 9,25 |
| 19,5 | 8,5 | 10 |
| 20,0 | 9,25 | 10,75 |
| 20,5 | 10 | 11,5 |
| 21,0 | 10,75 | 12,25 |
| 21,5 | 11,5 | 13 |
| 22,0 | 12,25 | 13,75 |
| 22,5 | 13 | 14,5 |
| 23,0 | 13,75 | 15,25 |
| 23,5 | 14,5 | 16 |
| 24,0 | 15,25 | 16,75 |
| 24,5 | 16 | 17,5 |
| 25,0 | 16,75 | 18,25 |
| 25,5 | 17,5 | 19 |
| 26,0 | 18,25 | 19,75 |
| 26,5 | 19 | 20,5 |
| 27,0 | 19,75 | 21,25 |
| 27,5 | 20,5 | 22 |
| 28,0 | 21,25 | 22,75 |
| 28,5 | 22 | 23,5 |
| 29,0 | 22,75 | 24,25 |
| 29,5 | 23,5 | 25 |
| 30,0 | 24,25 | 25,75 |

Impureza e Quebrados usam o excesso sobre a tolerância enviada na carga. PH
usa o déficit abaixo do mínimo informado. Os parâmetros são opcionais e, na
ausência deles, não acrescentam desconto. A soma não pode atingir 100%.

```text
desconto kg = peso bruto × desconto total / 100
peso líquido = peso bruto - desconto kg
sacas = peso líquido / 60
```

## Snapshot da regra

`regra_desconto_aplicada` é somente leitura e congela a regra efetivamente
usada. O snapshot contém:

- método e versão da tabela de umidade;
- cultura e origem das regras de classificação;
- medição, grupo cultural, fonte, versão e desconto da umidade;
- medições, tolerâncias, excessos ou déficit, taxas e descontos de impureza,
  quebrados e PH;
- desconto total percentual e em quilogramas.

Assim, uma futura mudança de parâmetros ou tabela não reescreve o cálculo das
cargas já registradas. Cargas históricas originadas por grupo registram
`grupo_colheita_legado` como origem; cargas novas registram
`parametros_da_carga`.

## APIs

Todas as rotas exigem autenticação JWT.

```text
GET    /api/graos/cargas-colhidas/
POST   /api/graos/cargas-colhidas/
GET    /api/graos/cargas-colhidas/{id}/
PATCH  /api/graos/cargas-colhidas/{id}/
DELETE /api/graos/cargas-colhidas/{id}/
```

Não existe mais rota pública `/api/graos/grupos-colheita/`.

A listagem aceita `propriedade`, `cad_pro`, `cultura`, `safra`, `armazem`,
`data_colheita`, `status`, `search` e `ordering`. A busca considera placa,
motorista, local de colheita, propriedade, CAD/PRO, cultura e safra. Os status
são `ativa`, `cancelada` e `substituida`.

Os filtros `propriedade` e `cad_pro` consideram todas as parcelas persistidas
do rateio. Quando combinados, devem corresponder à mesma parcela. A busca
textual também inclui o nome da propriedade e o código do CAD/PRO secundários.
Uma carga aparece uma única vez, mesmo que várias parcelas correspondam à
consulta. Os pesos retornados continuam sendo os da carga completa; o filtro
não transforma a listagem em um resumo de peso por propriedade.

Na interface, cargas compartilhadas exibem todas as propriedades e seus
CAD/PROs, com peso líquido e sacas de cada parcela do snapshot. O total da carga
fica identificado separadamente. A busca local também considera os produtores
secundários, e os botões de edição/cancelamento continuam atuando sobre a carga
inteira. Não há recálculo ou gravação de saldo para montar esse cartão.

Cargas históricas sem parcelas persistidas continuam sendo filtradas pelas
dimensões principais. Não se inferem novos rateios a partir dos vínculos atuais
entre CAD/PRO e propriedades. Os filtros de estado e período são mantidos.

### Criação

Exemplo mínimo, além das medições obrigatórias:

```json
{
  "propriedade": 1,
  "cad_pro": "9e12c603-51c8-42c6-89bb-d5719f297804",
  "cultura": "Soja",
  "safra": "2026/2027",
  "armazem": 4,
  "talhoes_selecionados": [8, 9],
  "data_colheita": "2026-08-23",
  "placa": "ABC1D23",
  "motorista": "João da Silva",
  "peso_bruto_kg": "30000.000",
  "umidade_percentual": "14.5",
  "impureza_percentual": "1.00",
  "defeitos_percentual": "0.50",
  "ph": "78.00",
  "destinado_semente": false,
  "observacoes": ""
}
```

`lote`, valores calculados, fingerprint, movimentação, snapshots, status e
auditoria são definidos pelo servidor.

O frontend envia uma `chave_registro` aleatória por viagem. Reenvios da mesma
tentativa continuam protegidos contra duplicidade, enquanto duas viagens reais
do mesmo veículo, no mesmo dia e com o mesmo peso podem ser registradas com
chaves diferentes. Integrações antigas sem a chave mantêm a proteção por
fingerprint canônico do contexto e da carga.

### Retificação por `PATCH`

Uma carga e sua movimentação nunca são reescritas. `PATCH` executa uma
retificação atômica:

1. resolve os CAD/PROs de todas as propriedades de destino, bloqueia em ordem
   estável todos os CAD/PROs e armazéns de origem e destino e estorna cada
   parcela da carga original;
2. registra uma nova carga com o contexto corrigido;
3. marca a original como `substituida` e grava `substituida_por`;
4. reverte toda a transação se o estorno ou a substituição falhar.

Campos omitidos são herdados da carga original, inclusive as regras congeladas
de classificação. `motivo_correcao` é opcional e somente de escrita. A resposta
HTTP 200 contém a carga substituta.

```json
{
  "peso_bruto_kg": "30120.000",
  "motivo_correcao": "Correção do ticket de balança"
}
```

Somente uma carga `ativa` pode ser retificada. Se o saldo já não puder ser
estornado com segurança, a operação retorna conflito e nada é alterado.

### Cancelamento por `DELETE`

`DELETE` representa cancelamento operacional: cria o estorno exato de cada parcela no ledger,
marca a carga como `cancelada` e registra usuário, instante e motivo. Nenhuma
linha de carga ou movimentação é apagada. O retorno de sucesso é HTTP 204.

O corpo pode informar `{"motivo": "Ticket lançado em duplicidade"}`. Repetir o
cancelamento não cria um segundo estorno.

Cancelar novamente uma carga já `cancelada` permanece idempotente. Tentar
cancelar uma versão `substituida` retorna HTTP 409 com `substituida_por`, para o
operador agir sobre a versão ativa e não perder silenciosamente sua intenção.

Duplicidade de carga e conflitos do ledger retornam HTTP 409. Demais violações
do contrato retornam HTTP 400.

### Integridade de rateios e concorrência

Movimentações ligadas à carga, inclusive parcelas secundárias do rateio, não
podem ser estornadas individualmente pelas rotas genéricas de movimentação ou
saldo. A API retorna HTTP 409 e orienta a corrigir ou cancelar a própria carga.
O parâmetro interno `permitir_carga_colhida` não é aceito como autorização pelo
contrato público da API.

Registro, cancelamento e correção bloqueiam o conjunto completo de CAD/PROs,
ordenado por UUID, antes dos armazéns e antes de processar a primeira parcela.
Na correção, esse conjunto inclui as parcelas antigas e novas, mesmo que seus
CAD/PROs não sejam os principais da carga. Isso impede que operações com CAD/PROs
cruzados adquiram bloqueios em ordens opostas. Os armazéns também são bloqueados
em ordem estável, incluindo origem e destino na correção.

Se uma parcela não puder ser estornada, inclusive por saldo reservado, toda a
operação é revertida: parcelas anteriores, saldos, origens de auditoria e status
da carga permanecem inalterados. O cancelamento repetido permanece idempotente.

## Banco e legado

`graos.0009_cargacolhida_contexto_direto_e_cancelamento` é aditiva. Ela:

- adiciona as dimensões diretas e os campos de ciclo de vida;
- confere a coerência entre grupo, armazém e lote durante o backfill;
- quando encontra divergência histórica, usa armazém e lote como dimensões do
  saldo físico e grava a divergência em `contexto_colheita`, sem apagar o grupo;
- preenche propriedade, CAD/PRO, cultura e safra das cargas antigas;
- reconhece como cancelada uma carga cujo movimento já possuía estorno;
- torna `grupo_colheita` opcional, sem apagar a tabela, os registros ou os
  vínculos históricos.

A reversão para `graos.0008` é bloqueada com mensagem explícita quando já
existirem cargas diretas sem grupo legado, pois remover essas dimensões causaria
perda de informação. Nesse cenário deve-se manter a migration ou restaurar um
backup compatível.

Não há migration destrutiva nesta entrega.
