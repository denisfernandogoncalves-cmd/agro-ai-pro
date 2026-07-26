# API de clima

Todos os endpoints exigem autenticação JWT.

## Consultar previsões

```http
GET /api/clima/previsoes/?propriedade=1&ordering=data
```

Filtros:

- `propriedade`: identificador exato;
- `data_inicio` e `data_fim`: datas ISO `AAAA-MM-DD`;
- `ordering`: `data`, temperaturas, chuva ou seus equivalentes com `-`.

Cada registro informa temperaturas mínima e máxima, chuva, probabilidade de
chuva, umidade média, vento máximo, código e descrição do tempo, alerta
agrícola, fonte e datas de atualização.

## Atualizar uma propriedade

```http
POST /api/clima/previsoes/atualizar/
Content-Type: application/json

{"propriedade": 1}
```

A propriedade precisa ter latitude e longitude. A resposta contém sete dias e
a operação atualiza registros já existentes sem duplicá-los.

## Provedor e erros

O sistema utiliza a API gratuita Open-Meteo, sem chave. A consulta possui
timeout de dez segundos. Indisponibilidade, resposta inválida ou coordenadas
ausentes retornam mensagem tratada; os dados anteriormente armazenados são
preservados.

## Alertas

- temperatura mínima até `3 °C`: risco de geada;
- temperatura máxima a partir de `35 °C`: calor intenso;
- chuva a partir de `50 mm`: chuva intensa;
- vento a partir de `40 km/h`: vento forte;
- umidade média até `30%`: umidade baixa.

Mais de um alerta pode ser emitido no mesmo dia.
