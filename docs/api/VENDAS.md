# Vendas com bloqueio por saldo

O módulo Comercial registra contratos de grãos vinculados obrigatoriamente a
uma `PosicaoSaldoGraos`. O contrato não é uma fonte paralela de estoque: todos
os efeitos usam os serviços públicos transacionais do app `graos`.

## Regras

- rascunho não altera saldo;
- confirmação chama `reservar_saldo` e bloqueia quantidade acima do disponível;
- entrega chama `confirmar_entrega`, reduzindo físico e comprometido;
- cancelamento chama `liberar_reserva` apenas para o saldo reservado aberto;
- devolução chama `registrar_devolucao`, recompõe físico e não reabre reserva;
- todos os mutadores exigem `Idempotency-Key` e rejeitam reuso conflitante;
- a posição consolidada exposta no detalhe é a dimensão autoritativa da venda;
- `lote_operacional` e `lote_operacional_codigo` identificam apenas o adaptador
  exigido pelos serviços do ledger e não representam origem física alocada;
- cargas e grupos de colheita não são atribuídos à venda sem uma regra explícita
  de alocação física.

## API autenticada

Base: `/api/comercial/vendas/`

- `GET /` — lista com filtros `search`, `status`, `cad_pro`, `propriedade`,
  `cultura`, `safra`, `classificacao_codigo` e `armazem`;
- `POST /` — cria rascunho;
- `GET /{id}/` — detalha contrato, posição autoritativa, entregas e devoluções;
- `POST /{id}/confirmar/` — cria a reserva oficial;
- `POST /{id}/cancelar/` — libera somente a reserva aberta;
- `POST /{id}/entregar/` — registra entrega parcial ou total;
- `POST /{id}/devolver/` — registra devolução parcial ou total.

Os `POST` exigem o cabeçalho `Idempotency-Key`. Repetição com o mesmo payload
devolve o efeito já realizado; payload diferente com a mesma chave retorna
conflito. Entregas e devoluções concorrentes com a mesma chave e o mesmo
payload são serializadas pela venda e devolvem o único efeito confirmado.
