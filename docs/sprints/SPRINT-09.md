# Sprint 9 — Máquinas

## Status

Concluída em 25/07/2026.

## Entregas

- cadastro de tratores, colheitadeiras, pulverizadores, implementos, caminhões
  e outros equipamentos;
- identificação única, marca, modelo, ano, propriedade e estado operacional;
- horímetro atual com bloqueio de regressão;
- uso vinculado a operação agrícola, operador e horas trabalhadas;
- abastecimentos com litros, custo, horímetro e documento opcional;
- manutenções agendadas e concluídas;
- históricos de uso e abastecimento imutáveis;
- filtros, busca, ordenação, administração, interface e documentação.

## Integridade

Usos e abastecimentos atualizam o horímetro com bloqueio transacional. Leituras
menores que a atual são rejeitadas. Máquinas fora do estado ativo não podem ser
usadas em operações. Registros históricos não aceitam edição nem exclusão.

## Migration

`maquinas.0001_initial` cria apenas tabelas e vínculos, sem alterar dados
anteriores. Nenhuma dependência nova ou serviço pago foi adicionado.
