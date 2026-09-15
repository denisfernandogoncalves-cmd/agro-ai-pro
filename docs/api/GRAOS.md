# API de Estoque de Grãos

## Seleção de lote para crédito de produção

Em Produção e Saldos, o seletor de crédito respeita todos os filtros da consulta:
propriedade produtora, CAD/PRO, cultura, safra, classificação e armazenagem.
A cultura ignora maiúsculas/minúsculas; safra e classificação seguem a
normalização da consulta de saldos. Lotes inativos ou sem CAD/PRO não são
oferecidos. Um lote que deixe de atender aos filtros não pode ser submetido.
Limpar os filtros permite consultar novamente os demais lotes elegíveis.

O recebimento manual de produção e o crédito atômico no saldo por CAD/PRO são
documentados em [Cargas Colhidas](CARGAS_COLHIDAS.md).

O módulo `apps.graos` mantém um ledger imutável e uma posição materializada para
o estoque físico e comprometido de grãos. Todas as rotas exigem autenticação
JWT e nenhuma operação altera dados fora de uma transação atômica.

## Pré-requisito

Esta versão depende de `cadpro.0001_initial`. O `LoteGraos` pode permanecer sem
CAD/PRO apenas para preservar cadastros históricos ainda sem movimentação. Todo
novo comando de saldo exige um lote com CAD/PRO ativo e vinculado à propriedade
produtora. A armazenagem é uma dimensão física independente e não determina a
propriedade da produção.

## Cargas diretas e legado de Grupo de Colheita

O fluxo operacional cria a carga diretamente com `propriedade`, `cad_pro`,
`cultura`, `safra` e `armazem`. O contrato público não expõe criação nem
manutenção de Grupo de Colheita.

O modelo e os registros históricos de Grupo de Colheita permanecem no banco
apenas como legado. A referência `grupo_colheita` da carga é anulável e não é
necessária para novas cargas. Não há rota pública de grupos no domínio de
grãos.

Criação, retificação, cancelamento e tabela de desconto por umidade estão
detalhados em [Cargas Colhidas](CARGAS_COLHIDAS.md).

## Posição de saldo

`PosicaoSaldoGraos` possui chave única composta por:

- propriedade produtora;
- CAD/PRO;
- cultura;
- safra;
- `classificacao_codigo`;
- armazém.

Ela armazena `saldo_fisico_kg`, `saldo_comprometido_kg` e `versao`. O campo
`saldo_disponivel_kg` é calculado como físico menos comprometido. A partir da
migration 0013, vendas podem deixar físico/disponível negativos e reservar acima
do físico. O comprometido permanece não negativo. Movimentos genéricos não
podem agravar déficits; entradas e liberações podem compensá-los parcialmente. Todos os
comandos bloqueiam a posição com `select_for_update()` antes de alterar saldos.

A capacidade de armazenagem soma somente o físico positivo de cada posição:
um déficit comercial não libera espaço ocupado por outra posição. Créditos e
devoluções ocupam espaço somente no trecho que superar o déficit existente.
Reconciliação recompõe os saldos assinados a partir do ledger. Reverter a
migration 0013 exige primeiro resolver os déficits; não há correção automática
de dados para reinstalar as constraints antigas.

## Ledger, origem e reserva

`MovimentacaoGraos` registra deltas assinados de saldo físico e comprometido,
operação, posição, origem, reserva opcional e movimento original em caso de
estorno. Cada linha também persiste `snapshot_anterior` e `snapshot_posterior`,
com os saldos físico, comprometido e disponível e a versão da posição. O ledger
é imutável na API, no admin, em `save()`/`delete()` do modelo e em
`QuerySet.update()`, `QuerySet.delete()` e `bulk_update()`.

`OrigemSaldoGraos` registra o tipo do comando, chave de idempotência, hash
canônico da requisição, referência externa, metadados e usuário. A chave é
obrigatória em todos os serviços mutadores, inclusive nos adaptadores legados.
Uma repetição idêntica devolve o resultado original sem novo efeito; reutilizar
a chave com outro conteúdo retorna conflito. O resultado original completo é
persistido nos metadados internos da origem no momento da execução. O replay
não consulta o saldo ou a reserva atuais para reconstruir a resposta.

`ResultadoOperacaoSaldo` e os DTOs de origem, posição, movimentação e reserva
não expõem models Django. Eles contêm somente strings, `Decimal`, tuplas e
mappings recursivamente congelados; snapshots, metadados e detalhes aninhados
também são imutáveis. A conversão para estruturas JSON mutáveis acontece
somente na borda HTTP.

`ReservaSaldoGraos` controla quantidade original, saldo ainda reservado e
status. Entregas e liberações parciais são permitidas. A reserva nunca pode
ficar negativa nem superar sua quantidade original.

## Serviços públicos

Disponíveis em `apps.graos.services`:

- `creditar_producao()` adiciona saldo físico;
- `reservar_saldo()` aumenta o saldo comprometido;
- `liberar_reserva()` reduz o compromisso sem saída física;
- `confirmar_entrega()` reduz físico e comprometido na mesma quantidade;
- `registrar_devolucao()` devolve quantidade ao saldo físico;
- `registrar_ajuste()` aplica deltas físicos e/ou comprometidos auditáveis;
- `estornar_movimentacao()` cria o inverso exato uma única vez; quando recebe
  qualquer perna de uma transferência, valida e estorna obrigatoriamente as duas
  pernas na mesma transação, sem permitir estorno individual;
- `transferir_saldo_fisico()` cria saída e entrada atômicas;
- `consultar_posicao()` aplica filtros por chave da posição;
- `reconciliar_posicao()` compara o snapshot com a soma do ledger e corrige
  divergências válidas.

Os comandos retornam `ResultadoOperacaoSaldo`, contrato imutável com `codigo`,
`origem`, `posicoes`, `movimentacoes`, `reserva`, `idempotente` e `detalhes`.
Eventos internos são agendados com `transaction.on_commit()` e publicados pelo
signal `apps.graos.events.saldo_graos_alterado` somente após confirmação.
Todos os mutadores validam que o CAD/PRO, o lote e o armazém aplicáveis
continuam ativos. O vínculo da produção com a propriedade é resolvido por
`CADProPropriedade`, nunca pela propriedade legada da armazenagem. Repetições idempotentes já concluídas
não executam nova mutação.

Quando uma operação precisa de mais de um lock, a ordem global é:

1. CAD/PROs em ordem de UUID;
2. armazéns em ordem de ID;
3. posições em ordem de ID;
4. reservas em ordem de ID;
5. movimentações auxiliares em ordem de ID.

Cargas rateadas adquirem os bloqueios de todos os CAD/PROs e armazéns da
operação antes da primeira parcela. As parcelas secundárias têm a mesma
proteção contra estorno genérico que a movimentação principal; devem ser
corrigidas ou canceladas pela API da própria carga.

## Endpoints de saldo

```text
GET  /api/graos/saldos/
GET  /api/graos/saldos/{id}/
GET  /api/graos/saldos/painel/
POST /api/graos/saldos/creditar-producao/
POST /api/graos/saldos/reservar/
POST /api/graos/saldos/liberar-reserva/
POST /api/graos/saldos/confirmar-entrega/
POST /api/graos/saldos/registrar-devolucao/
POST /api/graos/saldos/registrar-ajuste/
POST /api/graos/saldos/estornar-movimentacao/
POST /api/graos/saldos/transferir/
POST /api/graos/saldos/reconciliar/
GET  /api/graos/reservas/
GET  /api/graos/reservas/{id}/
GET  /api/graos/origens-saldo/
GET  /api/graos/origens-saldo/{id}/
```

## Rotas congeladas

As quatro rotas de integração congeladas são:

| Alias Django | Rota |
| --- | --- |
| `graos-producoes-creditar` | `POST /api/graos/producoes/creditar/` |
| `graos-ajustes` | `POST /api/graos/ajustes/` |
| `movimentacoes-graos-estornar` | `POST /api/graos/movimentacoes/{id}/estornar/` |
| `graos-transferencias` | `POST /api/graos/transferencias/` |

Elas reutilizam os mesmos serializers, serviços, autenticação e contratos de
erro dos endpoints de saldo e constam no OpenAPI.

A consulta de saldos e o painel aceitam `propriedade`, `cad_pro`, `cultura`,
`safra`, `classificacao_codigo` e `armazem`. O painel usa exclusivamente as
posições oficiais do ledger e devolve totais físico, comprometido e disponível,
consolidação por CAD/PRO e o detalhamento por cultura, safra, classificação e
armazenagem. O filtro `propriedade` seleciona diretamente a propriedade produtora
registrada na posição, inclusive quando o CAD/PRO é compartilhado entre propriedades.
O local de armazenagem e os demais vínculos do CAD/PRO não ampliam esse filtro.
O seletor de lotes para crédito usa a propriedade produtora do lote e impede a
submissão de um lote fora da seleção atual. Registros históricos sem propriedade
continuam visíveis na consulta geral, sem atribuição presumida a uma propriedade.
Reservas aceitam `posicao` e `status`;
origens aceitam `tipo` e busca por chave ou referência.

A consulta de movimentações aceita filtros por operação, posição, CAD/PRO,
classificação, armazém, propriedade e origem. Cada item expõe a identidade da
posição, o CAD/PRO, a armazenagem e a origem imutável, incluindo a chave de
idempotência, para rastreabilidade ponta a ponta.

O frontend oferece o módulo **Produção e saldos**, que consulta esse painel,
aplica os mesmos filtros dimensionais e registra produção pelo comando oficial
`creditar_producao`; não mantém uma segunda fonte de saldo.

Exemplo de crédito:

```json
{
  "lote": 1,
  "quantidade_kg": "30000.000",
  "data_movimento": "2026-08-06",
  "referencia_externa": "ROM-100",
  "chave_idempotencia": "producao:rom-100"
}
```

Exemplo de reserva:

```json
{
  "lote": 1,
  "quantidade_kg": "5000.000",
  "referencia_externa": "CONTRATO-10",
  "chave_idempotencia": "reserva:contrato-10"
}
```

Exemplo de retorno padronizado:

```json
{
  "sucesso": true,
  "codigo": "saldo_reservado",
  "idempotente": false,
  "origem": {},
  "posicoes": [],
  "movimentacoes": [],
  "reserva": {},
  "detalhes": {}
}
```

Conflitos operacionais retornam HTTP 409:

```json
{
  "sucesso": false,
  "codigo": "saldo_insuficiente",
  "mensagem": "Saldo disponível insuficiente."
}
```

## Endpoints legados preservados

Os CRUDs de armazéns e lotes e as consultas de movimentações permanecem em
`/api/graos/armazens/`, `/api/graos/lotes/` e
`/api/graos/movimentacoes/`. A criação legada de movimentação agora exige chave
de idempotência e delega ao núcleo transacional. Grupo de Colheita não integra
mais o contrato operacional público.

## Migrations

- `0002_cadpro_saldos_reservas_base.py`: adiciona a estrutura compatível e
  campos inicialmente anuláveis para dados legados;
- `0003_normalizar_lotes_existentes.py`: normaliza classificação, associa o
  único CAD/PRO ativo disponível e converte movimentos existentes para o novo
  ledger, incluindo snapshots sequenciais; aborta se um movimento não puder ser
  associado sem ambiguidade;
- `0004_saldos_constraints.py`: torna obrigatórios os vínculos do ledger e
  adiciona constraints e índices finais;
- `0009_cargacolhida_contexto_direto_e_cancelamento.py`: adiciona o contexto
  direto e o ciclo de cancelamento/substituição da carga; valida e preenche os
  dados históricos antes de tornar `grupo_colheita` opcional, sem apagar o
  modelo nem seus registros.

Na aplicação, as migrations são aditivas e não removem movimentos, lotes ou
saldos. Na reversão para `0001`, o esquema antigo não possui conceito de reserva:
eventos exclusivamente de compromisso e as tabelas novas são removidos em ordem
segura, enquanto todo delta físico é projetado para uma movimentação legada
equivalente. Isso evita falhas por `PROTECT`, preserva o saldo físico e torna
explícita a perda semântica inevitável de reservas no downgrade.

## Validação

```powershell
python manage.py check --settings=config.settings.test
python manage.py makemigrations --check --dry-run --settings=config.settings.test
python manage.py test apps.graos --settings=config.settings.test
python manage.py test --settings=config.settings.test
```

O ciclo de migration deve ser validado em SQLite descartável com
`0001 -> 0004 -> 0001 -> 0004`; não executar esse teste em banco persistente.

Os testes PostgreSQL usam `TransactionTestCase`, conexões independentes e
threads reais para validar: duas reservas concorrentes, dois créditos em
posições distintas disputando a capacidade do mesmo armazém, duas requisições
simultâneas com a mesma chave de idempotência, estorno concorrente com liberação,
estorno concorrente com entrega e transferências simultâneas em sentidos
opostos. Cada corrida verifica invariantes finais e trata qualquer deadlock de
banco não convertido em erro de domínio como falha. O banco deve ser descartável.

## Interface de transferência e identificação da produção (30/08/2026)

A aba **Transferência de saldo** fica imediatamente antes de **Vendas** e usa
POST `/api/graos/saldos/transferir/`. Primeiro são selecionadas **Cultura** e
**Ano/Safra**. A origem é selecionada por **Propriedade / CAD/PRO de origem /
Proprietário**, diretamente sobre uma posição oficial dessa cultura e safra com
saldo disponível. O proprietário vem do cadastro da propriedade; campo vazio
aparece como não informado. Classificação e armazenagem são mostradas na opção
para evitar ambiguidade, sem expor lotes ao usuário.

O destino usa **Propriedade / CAD/PRO de destino / Proprietário** e lista as
posições oficiais compatíveis, inclusive sem saldo. A API recebe
`posicao_origem` e `posicao_destino`; o lote permanece somente como adaptador
interno do ledger para compatibilidade histórica. Origem, destino, quantidade
em kg, data, referência e observações compõem o lançamento. Quantidades na interface usam ponto de milhar e vírgula decimal;
a API recebe decimal canônico. A confirmação informa o débito e o crédito.
A mesma tentativa reutiliza sua chave de idempotência e o histórico agrupa
as duas movimentações pela chave de origem.

Conforme a decisão de 30/08/2026, concluída na retomada de 31/08, transferências
aceitam CAD/PROs iguais ou diferentes, entre propriedades ou armazenagens
distintas. Cultura, safra e classificação devem coincidir. A própria posição
é recusada, inclusive quando dois lotes apontam para ela. Saldo
comprometido não pode ser transferido. Débito e crédito são atômicos e conservam
o total. Sem lote de destino compatível, a interface explica o bloqueio.
Os dois lados adquirem locks de CAD/PRO e lotes em ordem canônica, antes dos
armazéns e posições, inclusive em transferências concorrentes opostas.
A nova aba não oferece estorno. O histórico agrupa débito e crédito e apresenta
data, propriedades, CAD/PROs, armazenagens, produto, safra, classificação,
quantidade, referência, observações, usuário e data/hora do registro.

A impressão da aba de transferências usa uma planilha dedicada em A4 paisagem,
no padrão de Vendas. Cada transferência aparece uma única vez, reunindo débito
e crédito, com origem, destino, contexto produtivo, referência, observações e
registro. O rodapé totaliza a quantidade transferida; o formulário operacional
não é impresso.

Em Produção e saldos, títulos derivam da propriedade das posições filtradas,
não da descrição genérica do CAD/PRO compartilhado. Mudança de propriedade
consulta imediatamente os dados; filtros em edição ocultam resultados anteriores
até aplicar a consulta. Respostas atrasadas não substituem a consulta mais recente.

A impressão A4 de Produção e saldos utiliza uma planilha dedicada no mesmo
padrão visual de Vendas. Ela imprime somente as posições dos filtros aplicados,
com contexto de propriedade, CAD/PRO, cultura e safra, além dos totais físico,
comprometido e disponível. Formulários, cartões e rastreabilidade permanecem na
tela e são omitidos do papel.

O painel mantém `consolidado_cadpro` para compatibilidade e acrescenta
`consolidado_propriedade`: uma entrada por propriedade, com lista de CAD/PROs,
saldos e número de posições. `resumo.propriedades` conta propriedades distintas
identificadas; histórico sem propriedade permanece separado com identificação
explícita e não aumenta essa contagem. A interface mostra cartões por propriedade
e contagens independentes de propriedades, CAD/PROs e posições.
