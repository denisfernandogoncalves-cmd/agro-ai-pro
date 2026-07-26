# API do AGRO-AI-PRO

## Autenticação

Crie um usuário administrativo com `python manage.py createsuperuser` e obtenha um token:

```http
POST /api/auth/token/
Content-Type: application/json

{"username": "usuario", "password": "senha"}
```

Envie o access token nas chamadas protegidas:

```http
Authorization: Bearer <access_token>
```

O token pode ser renovado em `POST /api/auth/token/refresh/`.

## Autorização

O sistema usa escopo por propriedade com papéis administrador, gestor, operador e somente leitura. A Gestão Integrada da Produção adiciona escopo por CAD/PRO. IDs fora do escopo autorizado retornam HTTP 404; ações incompatíveis retornam HTTP 403.

Consulte [Controle multiusuário](../SEGURANCA-MULTIUSUARIO.md).

## Módulos

### Propriedades

`/api/propriedades/` oferece CRUD, busca, ordenação, KML, GeoJSON e permissões do usuário.

### Talhões

CRUD, histórico agronômico, produtividade, filtros, paginação e KML estão em [Talhões](TALHOES.md).

### Clima

Previsão de sete dias, histórico, atualização e alertas estão em [Clima](CLIMA.md).

### Mercado

Cotações de soja, milho, trigo e Brent, Corn Belt e notícias estão em [Mercado](MERCADO.md).

### Financeiro

Parceiros, categorias, centros de custo, contas a pagar e receber e liquidação estão em [Financeiro](FINANCEIRO.md).

### Estoque de insumos

Produtos, locais, lotes, movimentos, validade e estoque mínimo estão em [Estoque](ESTOQUE.md).

### Operações agrícolas

Planejamento, execução, custos e baixa transacional de insumos estão em [Operações](OPERACOES.md).

### Gestão Integrada da Produção

CAD/PRO, recebimentos, qualidade, estoque de grãos, transferências, contratos, embarques, relatórios, auditoria e importação de planilhas estão em [Produção Integrada](PRODUCAO-INTEGRADA.md).

### Máquinas

Frota, horímetro, uso, abastecimentos e manutenções estão em [Máquinas](MAQUINAS.md).

### Relatórios gerais

O Dashboard geral e o fluxo financeiro estão em [Relatórios](RELATORIOS.md).

### Assistente

Insights gerenciais explicáveis estão documentados em [IA](IA.md).
