# Sprint 14 — Integração Enterprise de Clima, Mercado e Produção

## Objetivo

Consolidar os três domínios como uma operação integrada, preservando a PR #16 e os
contratos existentes.

## Entregas

### Clima

- clima atual, horário e sete dias;
- worker, cache, deduplicação e backoff;
- riscos para pulverização e colheita;
- Dashboard e notificações internas.

### Mercado

- snapshots e séries diárias para sete ativos;
- PTAX/BCB e adaptador configurável de commodities;
- worker, cache, lock e tolerância a falhas;
- gráficos intradiário, cinco dias e trinta dias;
- análise de Corn Belt, Brent, dólar, estoque e contratos;
- integração ao Dashboard.

### Produção

- lotes conjuntos com duas ou mais propriedades;
- áreas efetivamente colhidas, talhões, CAD/PRO e cargas;
- saldo conjunto separado;
- sem rateio, rateio por área e rateio manual;
- saídas, transferências, ajustes e estornos;
- relatórios e tela responsiva em dez etapas.

## Segurança

- consultas operacionais isoladas por propriedade;
- lotes visíveis somente quando o usuário possui acesso a todas as propriedades;
- validação adicional de CAD/PRO;
- HTTP 404 para objetos externos e HTTP 403 para ação incompatível;
- nenhuma chave de provedor no frontend;
- migrations somente aditivas.

## Custos

Nenhum serviço pago foi ativado. PTAX utiliza dado aberto. O adaptador público de
commodities permanece restrito a desenvolvimento e homologação até validação de licença
para eventual uso comercial.

## Critério de conclusão

A Sprint somente pode ser considerada concluída após aprovação integral de backend,
frontend, build, migrations, Docker, whitespace e varredura de segredos no GitHub
Actions.
