# Lotes Conjuntos de Produção

## Objetivo

O recurso registra produção originada de duas ou mais propriedades quando a colheita,
a pesagem ou o armazenamento não permitem identificar uma quantidade real por origem.
A produção permanece conjunta até que o usuário escolha explicitamente um método de
rateio com informação confiável.

O módulo não transforma estimativas em produção individual real. Relatórios e APIs
identificam o método utilizado em cada distribuição.

## Arquitetura

O domínio está dentro do app `producao`, mas isolado em arquivos próprios:

- `joint_models.py`: entidades e restrições;
- `joint_services.py`: transações, saldos, rateios e auditoria;
- `joint_serializers.py`: contratos da API e gravação aninhada;
- `joint_views.py`: endpoints, filtros, ações e exportações;
- `test_lotes_conjuntos.py`: testes de domínio, API e permissões;
- `frontend/src/pages/LotesConjuntos`: fluxo responsivo de lançamento e conferência.

As entidades existentes são reutilizadas:

- `Propriedade` e `AcessoPropriedade`;
- `Talhao`;
- `CadPro` e `AcessoCadPro`;
- `Cultura` e `Safra`;
- `LocalEstoque`;
- `Motorista` e `Veiculo`;
- `ParceiroFinanceiro` e `ContratoProducao`;
- `SaldoGraos` e `MovimentacaoGraos`;
- `AuditoriaProducao`.

Não foi criado um segundo cadastro de propriedades, CAD/PRO, motoristas, veículos,
locais ou contratos.

## Modelo de dados

### LoteConjuntoProducao

Cabeçalho do lote com código automático, cultura, variedade, safra, período de
colheita, armazenagem, modo de rateio, totais calculados, qualidade média, usuário e
situação.

Situações:

- `rascunho`;
- `conferencia`;
- `confirmado`;
- `encerrado`;
- `estornado`.

### ParticipanteLoteConjunto

Relaciona o lote com cada propriedade participante. A restrição de unicidade impede
que a mesma propriedade seja repetida dentro do lote.

Registra:

- propriedade;
- CAD/PRO opcional;
- área cadastrada;
- área efetivamente colhida;
- percentual da área;
- quantidade rateada, quando houver;
- método e justificativa do rateio;
- autorização e justificativa para excesso de área.

### TalhaoParticipanteLoteConjunto

Relaciona os talhões utilizados e suas áreas colhidas. O talhão deve pertencer à
propriedade do participante.

### CargaLoteConjunto

Registra viagens, motorista, cavalo, carreta, placas legadas normalizadas,
transportadora, origem, destino, pesos, qualidade, romaneio, balança, nota fiscal e
local de armazenagem.

Os totais e as médias de qualidade do lote são sempre recalculados a partir das
cargas.

### SaldoLoteConjunto e MovimentacaoLoteConjunto

Mantêm o estoque ainda não distribuído. O saldo conjunto é separado dos saldos
individuais por propriedade e CAD/PRO.

Cada movimentação registra:

- tipo;
- quantidade;
- origem e destino;
- saldo anterior e posterior;
- participante e CAD/PRO, quando aplicável;
- usuário, data, referência, motivo e estorno.

### CadProLoteConjunto

Registra distribuições explícitas do lote para CAD/PRO autorizados. A soma distribuída
não pode superar o saldo conjunto.

### SaidaLoteConjunto

Permite saída parcial ou total do saldo ainda conjunto, com comprador, contrato,
motorista, veículos, placas, romaneio, notas e destino. A confirmação é transacional
e impede saldo negativo ou dupla baixa.

## Áreas e produtividade

A área total cadastrada e a área total efetivamente colhida são somadas a partir dos
participantes.

A produtividade conjunta utiliza exclusivamente a área efetivamente colhida:

```text
produtividade_kg_ha = peso_liquido_total_kg / area_total_colhida_ha
produtividade_sacas_ha = quantidade_sacas / area_total_colhida_ha
```

A área cadastrada é sugestão. Quando a área colhida superar a disponível, somente
administrador pode autorizar e deve informar justificativa. A autorização fica
registrada no participante e na auditoria.

## Modos de rateio

### Conjunta sem rateio

É o padrão. O saldo permanece em `SaldoLoteConjunto` e não gera produção individual
por propriedade ou CAD/PRO.

### Rateio automático pela área

Distribui o saldo proporcionalmente à área efetivamente colhida. Cada parcela é
arredondada para três casas decimais em quilogramas e a última recebe o ajuste de
arredondamento, preservando exatamente o total.

O método é identificado como `area`, ou produção estimada por área.

### Rateio manual

Recebe valores em quilogramas, toneladas ou sacas. A unidade-base interna é o
quilograma. A confirmação exige justificativa e valida que a soma seja igual ao saldo
que será distribuído.

O método é identificado como `manual`, ou produção ajustada manualmente.

## Fluxo de estoque

1. O lote é criado em rascunho.
2. Propriedades, áreas, talhões, CAD/PRO e cargas são conferidos.
3. A confirmação cria uma entrada em `SaldoLoteConjunto`.
4. Sem rateio, o estoque permanece conjunto.
5. Com distribuição explícita, o serviço debita o saldo conjunto.
6. O mesmo serviço credita o `SaldoGraos` existente da propriedade e do CAD/PRO.
7. Saídas, transferências, ajustes e estornos usam bloqueio de linha e transação.
8. Nenhum saldo pode ficar negativo.

## Permissões

O usuário só visualiza um lote quando possui acesso a todas as propriedades
participantes.

- superusuário: acesso integral;
- administrador: cria, confirma, rateia, ajusta e estorna;
- gestor: cria, confirma, rateia e consulta;
- operador: inclui cargas e executa movimentações permitidas;
- somente leitura: consulta.

Além da propriedade, qualquer CAD/PRO informado exige vínculo ativo em
`AcessoCadPro`.

Recursos com propriedade externa ao escopo retornam HTTP 404. Ações incompatíveis
com o papel retornam HTTP 403. A proteção principal permanece no backend.

## Endpoints

```text
GET|POST   /api/producao/lotes-conjuntos/
GET|PATCH  /api/producao/lotes-conjuntos/{id}/
POST       /api/producao/lotes-conjuntos/{id}/recalcular/
POST       /api/producao/lotes-conjuntos/{id}/colocar-em-conferencia/
POST       /api/producao/lotes-conjuntos/{id}/confirmar/
POST       /api/producao/lotes-conjuntos/{id}/ratear-area/
POST       /api/producao/lotes-conjuntos/{id}/ratear-manual/
POST       /api/producao/lotes-conjuntos/{id}/transferir/
POST       /api/producao/lotes-conjuntos/{id}/ajustar-saldo/
POST       /api/producao/lotes-conjuntos/{id}/encerrar/
POST       /api/producao/lotes-conjuntos/{id}/estornar/
GET        /api/producao/lotes-conjuntos/{id}/resumo-transportes/
GET|POST   /api/producao/cargas-lotes-conjuntos/
GET|POST   /api/producao/saidas-lotes-conjuntos/
POST       /api/producao/saidas-lotes-conjuntos/{id}/confirmar/
POST       /api/producao/saidas-lotes-conjuntos/{id}/estornar/
GET        /api/producao/saldos-lotes-conjuntos/
GET        /api/producao/movimentacoes-lotes-conjuntos/
GET        /api/producao/relatorios-lotes-conjuntos/?formato=csv|xlsx|pdf
```

## Interface

A tela possui dez etapas:

1. informações básicas;
2. seleção de propriedades;
3. áreas colhidas;
4. CAD/PRO e talhões;
5. cargas e viagens;
6. qualidade;
7. armazenagem;
8. rateio opcional;
9. conferência;
10. confirmação.

O resumo em tempo real mostra quantidade de propriedades, áreas, produção total,
produtividade conjunta e saldo ainda não distribuído. O layout é responsivo e o
módulo é carregado sob demanda pelo shell Enterprise.

## Migration

`0003_lotes_conjuntos_producao.py` é aditiva e reversível. Ela cria somente novas
tabelas, chaves estrangeiras, índices, checks e restrições de unicidade. Não altera
nem exclui registros anteriores.

## Custos e privacidade

Nenhum serviço externo ou pago foi adicionado. PDF, XLSX e CSV reutilizam recursos
locais e bibliotecas open source já existentes no projeto. Nenhum dado, planilha,
credencial ou informação operacional é enviado a terceiros.
