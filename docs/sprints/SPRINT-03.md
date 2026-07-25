# Sprint 3 — Geoprocessamento

**Status:** parcialmente implementada
**Classificação registrada em:** 25/07/2026

## Escopo auditado

O Prompt Mestre prevê validação e armazenamento seguro de KML, tratamento de
coordenadas, polígonos e multipolígonos, erros de leitura e cálculo de área.

## Entregas existentes

- limite de upload de 5 MB e validação da extensão `.kml`;
- rejeição de XML com `DOCTYPE` ou entidades;
- validação de coordenadas e polígonos fechados não degenerados;
- leitura de Polygon e MultiPolygon;
- armazenamento da geometria em GeoJSON;
- centroide cartesiano destinado ao posicionamento visual;
- tratamento de erros com respostas de validação;
- testes automatizados do processamento KML.

## Pendências para conclusão

- cálculo de área geodésica em hectares com projeção apropriada;
- comparação entre área calculada e área declarada;
- renderização dos talhões e multipolígonos no frontend;
- definição de precisão, sistema de referência e estratégia para geometrias
  complexas;
- critérios formais de aceite e auditoria funcional da Sprint.

O centroide existente não representa cálculo oficial de área. Nenhuma nova
funcionalidade geoespacial foi criada durante esta harmonização documental.
