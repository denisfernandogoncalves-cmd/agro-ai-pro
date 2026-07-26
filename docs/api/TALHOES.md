# API de talhões

Todos os endpoints exigem autenticação JWT.

## Talhões

- `GET /api/talhoes/talhoes/`: lista paginada;
- `POST /api/talhoes/talhoes/`: cria um talhão;
- `GET|PUT|PATCH|DELETE /api/talhoes/talhoes/{id}/`: consulta e mantém um
  talhão.

Use `multipart/form-data` quando houver KML.

### Campos

`propriedade`, `nome` e `area_hectares` são obrigatórios. Também estão
disponíveis:

- `cultura_atual`, `safra`, `tipo_solo` e `observacoes`;
- `altitude_media` e `declividade_media`;
- `produtividade_esperada` e `produtividade_realizada`;
- `arquivo_kml`;
- `geometria_geojson`, `latitude_centro` e `longitude_centro`, somente leitura.

A área deve ser positiva e a soma das áreas dos talhões não pode superar a área
da propriedade. As produtividades, quando informadas, não podem ser negativas.

### Consulta

Parâmetros suportados:

- `search`: nome do talhão ou propriedade, cultura, safra e tipo de solo;
- `propriedade`: identificador exato da propriedade;
- `cultura` e `safra`: filtros exatos, sem diferença entre maiúsculas e
  minúsculas;
- `ordering`: nome, área, cultura, safra, produtividades e datas;
- `page` e `page_size`: paginação, limitada a 100 registros por página.

Quando `page` ou `page_size` é informado, a resposta contém `count`, `next`,
`previous` e `results`. Sem esses parâmetros, a API preserva o contrato
anterior e retorna uma lista simples.

## Histórico agronômico

- `GET /api/talhoes/historicos-agronomicos/`;
- `POST /api/talhoes/historicos-agronomicos/`;
- `GET|PUT|PATCH|DELETE
  /api/talhoes/historicos-agronomicos/{id}/`.

Cada registro contém `talhao`, `data_referencia`, `cultura`, `safra`,
produtividade esperada, produtividade realizada e observações. A listagem
aceita `talhao`, `search`, `ordering`, `page` e `page_size`.

Um histórico deve conter pelo menos um dado agronômico além da data. Talhões
com histórico não podem ser excluídos; a API retorna HTTP 409 até que os
registros relacionados sejam tratados explicitamente.

Os valores de produtividade são decimais não negativos. A API não converte
unidades: valores comparados dentro da mesma cultura e safra devem usar a mesma
unidade operacional.

## KML e geoprocessamento

O arquivo é opcional, limitado a 5 MB e deve usar extensão `.kml`. XML com
`DOCTYPE` ou entidades é recusado. O KML deve conter um polígono fechado, não
degenerado, com pelo menos três vértices distintos e coordenadas geográficas
válidas.

Respostas bem-sucedidas incluem `geometria_geojson` (`Polygon` ou
`MultiPolygon`) e o centroide visual. Erros de validação retornam HTTP 400 com
mensagens associadas aos campos.

O centroide é uma aproximação cartesiana destinada somente ao posicionamento
visual. A API não calcula área oficial a partir das coordenadas; o cálculo
geodésico permanece no escopo da Sprint 3.
