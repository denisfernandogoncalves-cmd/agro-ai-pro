# API de Operações

Todos os endpoints exigem JWT e usam o prefixo `/api/producao/`.

## Operações agrícolas

- `GET|POST /operacoes/`
- `GET|PUT|PATCH|DELETE /operacoes/{id}/`
- `POST /operacoes/{id}/iniciar/`
- `POST /operacoes/{id}/concluir/`
- `POST /operacoes/{id}/cancelar/`

Uma operação informa talhão, tipo, descrição, data planejada, área,
responsável, custo estimado e observações. A área não pode superar a área do
talhão. O backend preenche o usuário responsável pelo cadastro.

Somente operações planejadas aceitam edição ou exclusão. O início aceita
`data_inicio`; a conclusão aceita `data_conclusao` e `custo_realizado`.

Filtros: `status`, `tipo`, `talhao` e `propriedade`. A busca consulta descrição,
responsável, talhão e observações. A ordenação aceita data, tipo, estado e
custo estimado.

## Insumos

- `GET|POST /insumos/`
- `GET|PUT|PATCH|DELETE /insumos/{id}/`

O consumo associa uma operação a um lote e registra quantidade planejada e
quantidade efetivamente utilizada. Um mesmo lote aparece no máximo uma vez em
cada operação.

Ao concluir a operação, a quantidade utilizada — ou a planejada quando a
utilizada não foi informada — gera uma saída imutável no estoque. A conclusão
é atômica: falta de saldo em qualquer lote cancela todas as baixas daquela
tentativa. Depois do encerramento, consumos não podem ser editados ou
excluídos.
