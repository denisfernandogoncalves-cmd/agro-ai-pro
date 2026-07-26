# API Financeira

Todas as rotas exigem autenticação JWT.

## Cadastros auxiliares

- `/api/financeiro/categorias/`
- `/api/financeiro/parceiros/`
- `/api/financeiro/centros-custo/`

As três coleções oferecem CRUD, busca e ordenação. Categorias em uso,
parceiros vinculados e centros com lançamentos não podem ser excluídos.

## Lançamentos

- `GET|POST /api/financeiro/lancamentos/`
- `GET|PUT|PATCH|DELETE /api/financeiro/lancamentos/{id}/`
- `POST /api/financeiro/lancamentos/{id}/liquidar/`
- `POST /api/financeiro/lancamentos/{id}/cancelar/`
- `GET /api/financeiro/lancamentos/resumo/`

Filtros:

- `tipo`: `pagar` ou `receber`;
- `status`: `pendente`, `liquidado` ou `cancelado`;
- `categoria`, `parceiro`, `centro_custo` e `propriedade`: IDs;
- `safra`;
- `vencimento_inicio` e `vencimento_fim`;
- `search` e `ordering`.

Para liquidar:

```json
{
  "data_liquidacao": "2026-07-25",
  "valor_liquidado": "1500.00"
}
```

O resumo retorna valores a pagar, a receber, saldos previsto e realizado,
entradas, saídas, total atrasado e quantidade pendente.
