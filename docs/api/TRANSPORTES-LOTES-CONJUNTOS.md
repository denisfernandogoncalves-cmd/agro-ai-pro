# API — Relatórios de Transporte dos Lotes Conjuntos

O endpoint consolida exclusivamente cargas de lotes que o usuário pode visualizar.
Como um lote conjunto pode reunir várias propriedades sem rateio, a quantidade
transportada não é duplicada entre propriedades participantes.

```http
GET /api/producao/relatorios-transportes-conjuntos/
```

## Agrupamentos

Parâmetro `agrupamento`:

- `motorista`: quantidade, viagens e peso médio por motorista;
- `placa`: quantidade, viagens e peso médio por placa do cavalo;
- `periodo`: consolidação por data da viagem;
- `lote`: consolidação por lote conjunto;
- `destino`: consolidação por destino;
- `transportadora`: consolidação por transportadora.

Exemplos:

```http
GET /api/producao/relatorios-transportes-conjuntos/?agrupamento=motorista&formato=csv
GET /api/producao/relatorios-transportes-conjuntos/?agrupamento=placa&formato=xlsx
GET /api/producao/relatorios-transportes-conjuntos/?agrupamento=periodo&formato=pdf
```

## Filtros

- `lote`;
- `motorista`;
- `veiculo`;
- `transportadora`;
- `destino`;
- `cultura`;
- `safra`;
- `propriedade`;
- `data_inicio`;
- `data_fim`.

O filtro de propriedade seleciona lotes que incluem a propriedade, mas mantém a
quantidade como conjunta. Ele não inventa uma parcela individual para a propriedade.

## Formatos

- CSV;
- XLSX;
- PDF.

Os arquivos são gerados localmente pelo backend usando recursos open source já
instalados. Nenhum conteúdo é enviado a serviço externo.
