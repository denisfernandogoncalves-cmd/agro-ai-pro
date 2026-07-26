# AGRO-AI-PRO

**Versão funcional:** 1.0

Plataforma modular de gestão agrícola com backend Django REST Framework e
frontend React/TypeScript.

## Estado atual

As Sprints 1 (Infraestrutura + Propriedades), 2 (Talhões), 3
(Geoprocessamento), 4 (Clima), 5 (Mercado), 6 (Financeiro), 7 (Estoque), 8
(Operações), 9 (Máquinas), 10 (Relatórios), 11 (IA) e 12 (Aplicativo) estão
concluídas.

O sistema oferece:

- autenticação JWT;
- CRUD autenticado de propriedades;
- busca, ordenação e validação dos dados;
- upload e validação de polígonos KML;
- mapa com OpenStreetMap;
- proteção dos vínculos entre propriedades e talhões;
- testes automatizados da API.

O módulo de Talhões oferece CRUD autenticado, produtividade esperada e
realizada, histórico agronômico, filtros, busca, ordenação, paginação, interface
dedicada e mapa. O geoprocessamento valida KML, preserva Polygon e MultiPolygon
em GeoJSON, calcula a área geodésica aproximada, compara a medição com a área
declarada e enquadra geometrias complexas no mapa.

Talhões com histórico agronômico possuem exclusão protegida. A API mantém
compatibilidade com listagens antigas sem paginação e oferece respostas
paginadas quando `page` ou `page_size` é informado.

O módulo de Clima consulta gratuitamente a Open-Meteo, mantém previsão de sete
dias por propriedade e apresenta temperaturas, chuva, umidade, vento e alertas
agrícolas. As consultas persistidas continuam disponíveis durante falhas
temporárias do provedor.

O módulo de Mercado acompanha referências mensais globais de soja, milho,
trigo e petróleo Brent, exibe histórico e variação, monitora cinco regiões do
Corn Belt e reúne notícias cadastradas com fontes HTTPS.

O módulo Financeiro controla contas a pagar e receber, categorias, parceiros,
centros de custo, propriedades e safras, com liquidação, atrasos e resumo de
fluxo de caixa.

O módulo de Estoque controla insumos, defensivos, fertilizantes e sementes por
local e lote. Entradas e saídas preservam custo, documento fiscal opcional,
propriedade, safra e usuário responsável. O sistema bloqueia saídas sem saldo e
alerta sobre validade e estoque mínimo.

O módulo de Operações planeja e acompanha atividades agrícolas por talhão,
responsável, área e custo. A conclusão baixa os insumos efetivamente usados no
estoque de forma transacional e mantém a rastreabilidade entre operação, lote,
propriedade, safra e usuário.

O módulo de Máquinas controla frota, propriedade, estado, horímetro, uso em
operações, abastecimentos e manutenções. Leituras não podem regredir e os
históricos de campo e combustível são imutáveis.

O dashboard gerencial consolida estrutura, caixa, operações, estoque, máquinas,
alertas e fluxo mensal, com filtros por propriedade e safra.

O assistente gerencial gera insights explicáveis a partir de alertas e
pendências do próprio sistema, sem compartilhar dados com serviços externos.

O frontend pode ser instalado como aplicativo web em navegadores compatíveis.
O shell visual funciona offline; consultas e alterações continuam protegidas e
dependem de conexão com a API.

O índice oficial de andamento está em
[`documentos/SPRINTS.md`](documentos/SPRINTS.md).

## Execução local

### Backend

Crie um ambiente virtual e instale as dependências:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements\dev.txt
```

Configure as variáveis a partir de `.env.example`, inicialize o PostgreSQL e:

```powershell
cd backend
..\.venv\Scripts\python.exe manage.py migrate
..\.venv\Scripts\python.exe manage.py createsuperuser
..\.venv\Scripts\python.exe manage.py runserver
```

Para testes não é necessário PostgreSQL:

```powershell
$env:DJANGO_SETTINGS_MODULE='config.settings.test'
..\.venv\Scripts\python.exe manage.py test
```

### Frontend

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Defina `VITE_API_URL` quando a API não estiver em
`http://127.0.0.1:8000/api`.

## Docker

Com o Docker Desktop ativo:

```powershell
docker compose up --build
```

O sistema fica disponível em `http://127.0.0.1:5173` e o backend também pode
ser consultado em `http://127.0.0.1:8000/api/health/`. O Compose inicia
PostgreSQL, Redis, backend e frontend, aguardando os healthchecks dos serviços.

Se alguma porta já estiver em uso, defina `POSTGRES_PORT_EXPOSED`,
`REDIS_PORT_EXPOSED`, `BACKEND_PORT` e `FRONTEND_PORT` antes de executar o
Compose.

## Documentação

- [Prompt Mestre](docs/PROMPT-MESTRE-AGRO-AI-PRO.md)
- [Sprint 1](docs/sprints/SPRINT-01.md)
- [Sprint 2](docs/sprints/SPRINT-02.md)
- [Sprint 3](docs/sprints/SPRINT-03.md)
- [Sprint 4](docs/sprints/SPRINT-04.md)
- [Sprint 5](docs/sprints/SPRINT-05.md)
- [Sprint 6](docs/sprints/SPRINT-06.md)
- [API](docs/api/README.md)
- [Arquitetura](ARCHITECTURE.md)
