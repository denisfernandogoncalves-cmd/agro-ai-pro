# Sprint 3 — Geoprocessamento

**Status:** concluída
**Conclusão registrada em:** 25/07/2026

## Escopo auditado

O Prompt Mestre prevê validação e armazenamento seguro de KML, tratamento de
coordenadas, polígonos e multipolígonos, erros de leitura e cálculo de área.

## Entregas

- limite de upload de 5 MB e validação da extensão `.kml`;
- rejeição de XML com `DOCTYPE` ou entidades;
- validação de coordenadas e polígonos fechados não degenerados;
- leitura de Polygon e MultiPolygon;
- armazenamento da geometria em GeoJSON;
- centroide cartesiano destinado ao posicionamento visual;
- tratamento de erros com respostas de validação;
- cálculo geodésico aproximado da área em hectares;
- comparação informativa entre as áreas calculada e declarada;
- persistência da área calculada para propriedades e talhões;
- renderização completa de `Polygon` e `MultiPolygon`, incluindo anéis internos;
- enquadramento automático da geometria no mapa;
- testes automatizados do processamento, cálculo e frontend.

## Precisão e sistema de referência

As coordenadas KML são interpretadas como longitude e latitude no WGS84
(`EPSG:4326`). A área é calculada sobre a esfera autálica do WGS84, com raio de
`6.371.007,1809 m`. Essa transformação preserva área global e evita selecionar
uma zona UTM inadequada para geometrias que atravessem limites de zona.

O resultado é armazenado com quatro casas decimais em hectares. O primeiro anel
de cada polígono é tratado como perímetro externo; os demais são descontados
como áreas internas. Múltiplos polígonos são somados e diferenças de longitude
são normalizadas para geometrias próximas ao antimeridiano.

A medição é adequada para conferência operacional. Não substitui levantamento
topográfico certificado. O centroide continua sendo uma aproximação cartesiana
destinada somente ao posicionamento visual.

## Comparação das áreas

A API expõe a diferença assinada em hectares e em percentual:

- valor positivo: a área calculada é maior que a declarada;
- valor negativo: a área calculada é menor que a declarada;
- valor nulo: não existe geometria calculada.

A divergência é informativa e não bloqueia o cadastro, pois o projeto ainda não
possui tolerância agronômica oficial definida.

## Critérios de aceite

- [x] KML inválido é recusado com mensagem tratada;
- [x] Polygon, MultiPolygon e anéis internos são processados;
- [x] área calculada é persistida e apresentada pela API;
- [x] diferença para a área declarada é apresentada sem alterar o dado original;
- [x] geometrias complexas são exibidas e enquadradas no frontend;
- [x] migrations não possuem divergências;
- [x] testes do backend, componentes e build de produção são aprovados.

## Validação

- `manage.py check`: aprovado;
- `makemigrations --check --dry-run`: nenhuma divergência;
- testes backend: 35 aprovados;
- testes frontend: 5 aprovados;
- build de produção do frontend: aprovado.
