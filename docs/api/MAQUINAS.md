# API de Máquinas

Endpoints autenticados sob `/api/maquinas/`:

- `maquinas/`: cadastro e filtros por tipo, estado e propriedade;
- `usos/`: histórico imutável vinculado a uma operação agrícola;
- `abastecimentos/`: histórico imutável de combustível, custo e documento;
- `manutencoes/`: agenda e acompanhamento;
- `POST manutencoes/{id}/concluir/`: registra data, horímetro e custo.

O horímetro nunca pode regredir. O uso exige máquina ativa, leitura inicial
igual ou superior à atual e leitura final superior à inicial.
