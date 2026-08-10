# API de Estoque de Grãos

O módulo `apps.graos` mantém um ledger imutável e uma posição materializada para
o estoque físico e comprometido de grãos. Todas as rotas exigem autenticação
JWT e nenhuma operação altera dados fora de uma transação atômica.

## Pré-requisito

Esta versão depende de `cadpro.0001_initial`. O `LoteGraos` pode permanecer sem
CAD/PRO apenas para preservar cadastros históricos ainda sem movimentação. Todo
novo comando de saldo exige um lote com CAD/PRO ativo e vinculado à propriedade
do armazém.

## Posição de saldo

`PosicaoSaldoGraos` possui chave única composta por:

- CAD/PRO;
- cultura;
- safra;
- `classificacao_codigo`;
- armazém.

Ela armazena `saldo_fisico_kg`, `saldo_comprometido_kg` e `versao`. O campo
`saldo_disponivel_kg` é calculado como físico menos comprometido. Constraints de
banco impedem saldos negativos e comprometimento superior ao físico. Todos os
comandos bloqueiam a posição com `select_for_update()` antes de alterar saldos.

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
Todos os mutadores validam que o CAD/PRO, seu vínculo com a propriedade, o lote
e o armazém aplicáveis continuam ativos. Repetições idempotentes já concluídas
não executam nova mutação.

Quando uma operação precisa de mais de um lock, a ordem global é:

1. armazéns em ordem de ID;
2. posições em ordem de ID;
3. reservas em ordem de ID;
4. movimentações auxiliares em ordem de ID.

## Endpoints de saldo

```text
GET  /api/graos/saldos/
GET  /api/graos/saldos/{id}/
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

A consulta de saldos aceita `cad_pro`, `cultura`, `safra`,
`classificacao_codigo` e `armazem`. Reservas aceitam `posicao` e `status`;
origens aceitam `tipo` e busca por chave ou referência.

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
de idempotência e delega ao núcleo transacional.

## Migrations

- `0002_cadpro_saldos_reservas_base.py`: adiciona a estrutura compatível e
  campos inicialmente anuláveis para dados legados;
- `0003_normalizar_lotes_existentes.py`: normaliza classificação, associa o
  único CAD/PRO ativo disponível e converte movimentos existentes para o novo
  ledger, incluindo snapshots sequenciais; aborta se um movimento não puder ser
  associado sem ambiguidade;
- `0004_saldos_constraints.py`: torna obrigatórios os vínculos do ledger e
  adiciona constraints e índices finais.

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
