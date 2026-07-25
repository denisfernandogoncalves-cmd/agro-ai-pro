# Sprint 1 — Infraestrutura e Propriedades

**Status:** concluída em 25/07/2026
**Branch de trabalho:** `modulo-propriedades-v2`

## Objetivo

Entregar a base executável do AGRO-AI-PRO e o módulo de propriedades rurais, com
API REST autenticada, interface web, mapa, upload KML seguro e testes automatizados.

## Entregas

- CRUD de propriedades na API e no frontend;
- autenticação JWT obrigatória para acesso aos dados;
- busca por nome, proprietário, município ou UF;
- ordenação por nome, município, área ou data de criação;
- validação de área, UF, latitude e longitude;
- upload de arquivo `.kml` limitado a 5 MB;
- rejeição de XML inválido, declarações `DOCTYPE`, coordenadas inválidas e
  geometrias sem polígono;
- cálculo do centroide do polígono KML sem dependência geoespacial externa;
- mapa OpenStreetMap com marcador e polígono importado;
- proteção contra exclusão de propriedades que possuam talhões;
- configuração TypeScript/Vite funcional;
- configuração de teste com SQLite, independente do PostgreSQL de desenvolvimento.

## API

Base: `/api/propriedades/`

| Método | Rota | Ação |
| --- | --- | --- |
| `GET` | `/api/propriedades/` | Lista e pesquisa |
| `POST` | `/api/propriedades/` | Cadastra |
| `GET` | `/api/propriedades/{id}/` | Consulta |
| `PATCH`/`PUT` | `/api/propriedades/{id}/` | Atualiza |
| `DELETE` | `/api/propriedades/{id}/` | Exclui quando não há talhões |

Todas as rotas requerem `Authorization: Bearer <token>`. Tokens são obtidos em
`POST /api/auth/token/`.

Parâmetros opcionais de listagem:

- `search`: busca textual;
- `ordering`: `nome`, `municipio`, `area_hectares` ou `criado_em`; use `-` para
  ordem decrescente.

## Critérios de aceite validados

- operações CRUD autenticadas;
- acesso anônimo rejeitado;
- entradas inválidas respondem HTTP 400 sem criar dados;
- KML válido calcula e persiste o centroide;
- KML inválido é rejeitado;
- exclusão com talhões responde HTTP 409 e preserva os registros;
- migrations consistentes;
- frontend TypeScript gera build de produção.

## Testes

```powershell
$env:DJANGO_SETTINGS_MODULE='config.settings.test'
..\.venv\Scripts\python.exe manage.py check
..\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
..\.venv\Scripts\python.exe manage.py test

cd ..\frontend
npm.cmd run build
```

O Docker Compose foi validado com `docker compose config`. A construção e a
execução dos containers requerem o Docker Desktop ativo.

## Limitações conhecidas

- o cálculo de área a partir do KML pertence à Sprint 3 (Geoprocessamento);
- refresh automático do token e recuperação de senha ainda não fazem parte do
  fluxo de autenticação;
- o frontend ainda não possui suíte de testes de componentes; o script disponível
  nesta Sprint é o build TypeScript/Vite.
