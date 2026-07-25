# AGRO-AI-PRO

Plataforma modular de gestão agrícola com backend Django REST Framework e
frontend React/TypeScript.

## Estado atual

A Sprint 1 (Infraestrutura + Propriedades) está concluída. O sistema oferece:

- autenticação JWT;
- CRUD autenticado de propriedades;
- busca, ordenação e validação dos dados;
- upload e validação de polígonos KML;
- mapa com OpenStreetMap;
- proteção dos vínculos entre propriedades e talhões;
- testes automatizados da API.

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

O backend fica em `http://127.0.0.1:8000`. O Compose atual inicia PostgreSQL,
Redis e backend; o frontend é executado separadamente nesta Sprint.

## Documentação

- [Prompt Mestre](docs/PROMPT-MESTRE-AGRO-AI-PRO.md)
- [Sprint 1](docs/sprints/SPRINT-01.md)
- [API](docs/api/README.md)
- [Arquitetura](ARCHITECTURE.md)
