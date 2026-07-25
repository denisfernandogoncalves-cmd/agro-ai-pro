# Testes

## Backend

A suíte Django cobre autenticação, CRUD, busca, ordenação, validações, KML e
integridade referencial:

```powershell
cd backend
$env:DJANGO_SETTINGS_MODULE='config.settings.test'
..\.venv\Scripts\python.exe manage.py check
..\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
..\.venv\Scripts\python.exe manage.py test --verbosity 2
```

## Frontend

O projeto ainda não possui testes de componentes. A validação disponível executa
o compilador TypeScript em modo estrito e gera o bundle de produção:

```powershell
cd frontend
npm.cmd run build
```

## Infraestrutura

Validação estática do Compose:

```powershell
docker compose config --quiet
```

Build e testes em containers exigem o Docker Desktop ativo.
