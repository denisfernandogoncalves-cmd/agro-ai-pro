# Sprint 5 — Mercado

**Status:** concluída
**Conclusão registrada em:** 25/07/2026

## Objetivo

Disponibilizar um painel autenticado de referência para soja, milho, trigo,
petróleo Brent e clima nas principais regiões do Corn Belt, com histórico,
variações, alertas e notícias cadastradas.

## Entregas

- histórico mensal de soja, milho, trigo e Brent;
- atualização idempotente a partir das séries públicas do FRED;
- valores em dólares por tonelada métrica ou barril;
- resumo do último período e variação percentual;
- gráfico histórico sem dependência adicional;
- previsão de sete dias para Iowa, Illinois, Indiana, Nebraska e Minnesota;
- alertas para geada, calor, chuva intensa e calor com baixa precipitação;
- cadastro autenticado de notícias com endereço HTTPS;
- filtros, ordenação, administração, API e interface dedicadas;
- tratamento de indisponibilidade externa sem apagar dados persistidos.

## Fontes e periodicidade

As séries `PSOYBUSDM`, `PMAIZMTUSDM`, `PWHEAMTUSDM` e `POILBREUSDM` são
publicadas pelo Federal Reserve Bank of St. Louis no FRED e têm origem no
Primary Commodity Prices do Fundo Monetário Internacional. São referências
globais mensais, não cotações locais ou intradiárias.

O clima usa a API gratuita Open-Meteo, com coordenadas representativas de cinco
estados do Corn Belt. A previsão não representa todas as áreas produtoras de
cada estado.

## Critérios de aceite

- [x] quatro produtos possuem histórico e valor mais recente;
- [x] a variação entre os dois últimos períodos é calculada;
- [x] o histórico pode ser filtrado e ordenado;
- [x] o Corn Belt apresenta previsão e alertas por região;
- [x] falhas das fontes externas retornam erro tratado;
- [x] atualizações repetidas não duplicam registros;
- [x] notícias exigem URL HTTPS;
- [x] APIs exigem autenticação JWT;
- [x] interface, testes, migration e documentação estão consistentes.

## Limitações e aviso

Os indicadores servem para apoio gerencial e não constituem recomendação
financeira, de compra ou de venda. Notícias são cadastradas por usuários
autenticados; o sistema não copia textos de portais nem usa agregadores pagos.

## Validação

- `manage.py check`: aprovado;
- `makemigrations --check --dry-run`: sem divergência;
- testes do backend: 60 aprovados;
- testes de componentes e geometria: 8 aprovados;
- build de produção do frontend: aprovado.
