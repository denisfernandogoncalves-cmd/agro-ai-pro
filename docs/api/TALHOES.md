# API de talhões

## Endpoints preservados

- `GET /api/talhoes/talhoes/`: lista talhões;
- `POST /api/talhoes/talhoes/`: cria um talhão (`multipart/form-data` quando houver KML);
- `GET|PUT|PATCH|DELETE /api/talhoes/talhoes/{id}/`: consulta e mantém um talhão.

## Campos e validações

`propriedade`, `nome` e `area_hectares` são obrigatórios. A área deve ser positiva e a soma das áreas dos talhões não pode superar a área informada da propriedade. Latitude e longitude do centro aceitam, respectivamente, `-90..90` e `-180..180`.

`arquivo_kml` é opcional, limitado a 5 MB e deve ter extensão `.kml`. XML com `DOCTYPE` ou entidades é recusado. O arquivo deve conter um polígono fechado, não degenerado, com ao menos três vértices distintos e coordenadas dentro dos limites geográficos.

Respostas bem-sucedidas incluem `geometria_geojson` (`Polygon`) e `latitude_centro`/`longitude_centro`, dados preparados para renderização no mapa. Erros de validação retornam HTTP 400 e mensagens em português associadas ao campo.

## Limitação geoespacial

O centroide é uma aproximação cartesiana destinada **somente ao posicionamento visual**. A API não calcula área oficial a partir de graus de latitude/longitude. Como o projeto não dispõe nesta Sprint de cálculo geodésico/projeção apropriada, `area_hectares` continua sendo a área declarada pelo usuário, sujeita às validações de consistência descritas acima.

## Exemplo de resposta

```json
{
  "id": 1,
  "propriedade": 1,
  "propriedade_nome": "Fazenda Modelo",
  "nome": "Talhão Norte",
  "area_hectares": "20.00",
  "latitude_centro": "-20.333333",
  "longitude_centro": "-49.333333",
  "geometria_geojson": {"type": "Polygon", "coordinates": [[[-50, -20], [-49, -20], [-49, -21], [-50, -20]]]}
}
```
