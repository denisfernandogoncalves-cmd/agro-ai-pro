# Sprint 8 — Operações

## Status

Concluída em 25/07/2026.

## Entregas

- planejamento de preparo do solo, plantio, adubação, pulverização, irrigação,
  colheita e outras operações;
- vínculo obrigatório com talhão e, por consequência, propriedade e safra;
- data planejada, área, responsável, custos estimado e realizado;
- estados planejada, em execução, concluída e cancelada;
- regras explícitas para início, conclusão e cancelamento;
- planejamento e registro da quantidade utilizada de insumos por lote;
- baixa transacional do estoque na conclusão;
- bloqueio integral da conclusão quando qualquer lote não possui saldo;
- imutabilidade da operação e dos consumos após o encerramento;
- filtros por estado, tipo, talhão e propriedade, busca e ordenação;
- interface de planejamento, acompanhamento, insumos e encerramento;
- administração, API, testes automatizados e documentação.

## Decisão de integridade

A conclusão e todas as saídas de estoque são executadas na mesma transação. Se
um insumo não possuir saldo, nenhuma baixa é gravada e a operação permanece em
execução. Cada consumo mantém o identificador da movimentação de estoque que o
originou.

Somente operações planejadas podem ser editadas ou excluídas. Operações em
execução podem receber ajustes de consumo, mas, depois de concluídas ou
canceladas, preservam integralmente o histórico.

Máquinas não fazem parte deste escopo e permanecem reservadas à Sprint 9.

## Migration

`producao.0001_initial` cria somente tabelas, índices e restrições. Não altera
nem remove dados existentes.

## Validação

- Django Check e migrations;
- testes completos do backend;
- testes de componentes do frontend;
- build de produção;
- Docker Compose;
- diff e auditoria de segredos.

Nenhuma dependência nova ou serviço pago foi adicionado.
