# API — Gestão Integrada da Produção

Base: `/api/producao/`

Todas as rotas exigem JWT. As consultas são filtradas pela propriedade e pelos CAD/PRO autorizados. Escritas respeitam os papéis da PR #16.

## Cadastros

| Recurso | Rota |
| --- | --- |
| Culturas | `culturas/` |
| Safras | `safras/` |
| CAD/PRO | `cadpros/` |
| Acessos por CAD/PRO | `acessos-cadpro/` |
| Motoristas | `motoristas/` |
| Veículos | `veiculos/` |
| Contratos | `contratos/` |

## Recebimentos

- `GET/POST recebimentos/`
- `GET/PATCH/DELETE recebimentos/{id}/` — alteração e exclusão somente em rascunho
- `POST recebimentos/{id}/confirmar/`
- `POST recebimentos/{id}/estornar/` com `{ "motivo": "..." }`

A confirmação cria uma entrada de grãos e atualiza o saldo na mesma transação.

## Estoque de grãos

- `GET saldos-graos/`
- `GET movimentacoes-graos/`
- `POST movimentacoes-graos/` para entrada, saída, transferência e ajustes autorizados
- `POST movimentacoes-graos/{id}/estornar/`

Filtros principais: `propriedade`, `cadpro`, `talhao`, `cultura`, `safra` e `local`.

Movimentações são imutáveis. Não há `PATCH` ou `DELETE`.

## Embarques

- `GET/POST embarques/`
- `GET/PATCH/DELETE embarques/{id}/` — alteração e exclusão somente em rascunho
- `POST embarques/{id}/confirmar/`
- `POST embarques/{id}/estornar/` com motivo obrigatório

A confirmação:

1. valida o contexto do contrato;
2. valida limite e tolerância;
3. valida saldo físico;
4. baixa o estoque;
5. cria um lançamento financeiro a receber;
6. registra auditoria.

## Dashboard

`GET dashboard-integrado/`

Filtros: `propriedade`, `cadpro`, `cultura` e `safra`.

Retorna produção, qualidade média, estoque disponível, embarques, receita, contratos abertos e agregações por propriedade, CAD/PRO e talhão.

## Relatórios

`GET relatorios-integrados/`

Filtros:

- `propriedade`
- `cadpro`
- `talhao`
- `cultura`
- `safra`
- `local`
- `data_inicio`
- `data_fim`

`formato` aceita `json`, `csv`, `xlsx` ou `pdf`.

## Importação

- `POST importacoes/` — multipart com `tipo`, `propriedade`, `cadpro`, `arquivo` e mapeamento opcional
- `POST importacoes/{id}/validar/` — refaz prévia com mapeamento manual
- `POST importacoes/{id}/confirmar/` — importa em transação única

Tipos: `recebimentos`, `movimentacoes` ou `embarques`.

Recebimentos e embarques importados permanecem em rascunho até confirmação operacional.

## Auditoria

`GET auditoria/`

Somente leitura, com busca por ação, entidade e usuário. O histórico registra estados anterior e novo, sem permitir alteração ou exclusão pela API.

## Respostas de segurança

- HTTP 401: sessão ausente ou inválida;
- HTTP 403: papel insuficiente em recurso autorizado;
- HTTP 404: propriedade, CAD/PRO ou registro fora do escopo;
- HTTP 409: conflito de saldo, estado, contrato ou estorno;
- HTTP 400: dados ou mapeamento inválidos.
