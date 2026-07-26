# Sprint 6 — Financeiro

**Status:** concluída
**Conclusão registrada em:** 25/07/2026

## Objetivo

Controlar contas a pagar e a receber com vínculos agrícolas, cadastros
auxiliares, liquidação segura e visão consolidada de fluxo de caixa.

## Entregas

- categorias de despesa, receita ou uso misto;
- fornecedores, clientes e parceiros mistos;
- centros de custo vinculáveis a propriedade e safra;
- contas a pagar e a receber;
- emissão, vencimento, liquidação, cancelamento e identificação de atrasos;
- vínculos opcionais com propriedade, safra, parceiro e centro de custo;
- filtros, busca e ordenação;
- resumo de valores previstos, realizados e atrasados;
- proteção contra exclusão de cadastros em uso;
- API autenticada, administração e interface responsiva;
- cadastros auxiliares e ações de liquidação na interface.

## Regras de integridade

- valores devem ser positivos;
- categoria de receita não pode ser usada em conta a pagar e vice-versa;
- liquidação exige data e valor;
- somente lançamentos pendentes podem ser liquidados ou cancelados;
- cadastros vinculados usam proteção referencial;
- lançamentos cancelados não entram no saldo previsto ou realizado.

## Critérios de aceite

- [x] CRUD dos cadastros auxiliares;
- [x] CRUD de contas a pagar e receber;
- [x] filtros por contexto agrícola e situação;
- [x] liquidação e cancelamento protegidos;
- [x] resumo de fluxo de caixa;
- [x] identificação de valores atrasados;
- [x] migration e constraints consistentes;
- [x] backend, frontend e documentação validados.

## Limitações

Não há leitura de código de barras, conciliação bancária, parcelamento ou
integração fiscal nesta Sprint. Esses itens exigem regras de negócio e
integrações específicas futuras.

## Validação

- `manage.py check`: aprovado;
- `makemigrations --check --dry-run`: sem divergência;
- testes do backend: 74 aprovados;
- testes de componentes e geometria: 9 aprovados;
- build de produção do frontend: aprovado.
