# Sprint 11 — Inteligência Artificial

## Status

Concluída em 25/07/2026.

## Entregas

- assistente gerencial autenticado e filtrável por propriedade;
- regras explicáveis para financeiro vencido, estoque vencido ou mínimo,
  operações e manutenções atrasadas e alertas climáticos;
- criticidade, evidência, ação sugerida e módulo de origem em cada insight;
- aviso explícito de que a recomendação não substitui avaliação profissional;
- interface, API, testes e documentação.

A versão 1 usa regras determinísticas auditáveis, não envia dados a terceiros,
não usa modelos externos e não gera custos. Não cria migration nem dependência.

## Evolução da V1 — 04/08/2026

O motor passou a consumir também o ledger oficial de grãos, sem alterar o
contrato público `regras_explicaveis_v1`. A integração acrescenta saldo por
propriedade e safra, alerta para lotes inativos com saldo e alerta de ocupação
de armazém a partir de 90%. A capacidade considera todos os lotes do armazém,
mesmo quando o saldo exibido está filtrado por safra.

A evolução não cria migration, dependência ou integração externa. Os testes
cobrem geração das regras, isolamento por propriedade e safra, limite de 90%,
saldo zero, capacidade compartilhada entre safras e saldos negativos. Déficits
inconsistentes não reduzem a ocupação calculada e geram alerta crítico próprio.
