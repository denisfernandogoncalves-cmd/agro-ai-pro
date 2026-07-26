# AGRO-AI-PRO

**Versão funcional:** 1.0  
**Em desenvolvimento:** interface Enterprise e Gestão Integrada da Produção Agrícola

Plataforma modular de gestão agrícola com backend Django REST Framework e frontend React/TypeScript.

## Estado atual

As Sprints 1 a 12 da versão 1.0 estão concluídas. A próxima evolução oficial adiciona controle multiusuário por propriedade e CAD/PRO, interface Enterprise e o domínio integrado de produção, estoque de grãos e comercialização.

O sistema oferece:

- autenticação JWT com renovação de sessão;
- autorização por propriedade com papéis administrador, gestor, operador e somente leitura;
- propriedades, talhões, KML e geoprocessamento;
- clima por propriedade e mercado agrícola;
- financeiro, estoque de insumos, operações e máquinas;
- relatórios, Dashboard Executivo, insights explicáveis e PWA;
- Gestão Integrada da Produção Agrícola em desenvolvimento.

## Gestão Integrada da Produção Agrícola

O novo módulo substitui controles legados em planilhas e integra:

- culturas, safras e múltiplos CAD/PRO por propriedade;
- acessos por CAD/PRO, preservando as permissões por propriedade;
- motoristas, veículos e terceiros por meio dos parceiros existentes;
- recebimentos com peso bruto, tara, peso líquido, sacas e indicadores de qualidade;
- estoque de grãos por propriedade, CAD/PRO, talhão, cultura, safra e armazenagem;
- entradas, saídas, transferências, ajustes e estornos, sem saldo negativo;
- contratos, embarques, romaneios e números de notas fiscais;
- criação automática de contas a receber após embarques confirmados;
- auditoria imutável dos eventos operacionais;
- Dashboard de produção, qualidade, estoque, contratos, embarques e receita;
- relatórios JSON, CSV, Excel e PDF;
- importação assistida de CSV, XLSX e XLSM com detecção de colunas, prévia, validação e confirmação;
- insights explicáveis sobre safras, produtividade, qualidade, estoque e cobertura contratual.

A arquitetura detalhada está em [`docs/PRODUCAO-INTEGRADA.md`](docs/PRODUCAO-INTEGRADA.md).

## Arquitetura resumida

- Backend: Django 5 + Django REST Framework
- Autenticação: Simple JWT
- Frontend: React 19 + Vite + TypeScript
- Mapas: React Leaflet + OpenStreetMap
- Banco de dados: PostgreSQL 17
- Cache: Redis ou cache local em desenvolvimento
- Testes: Django com SQLite em memória e verificações de componentes frontend
- Infraestrutura: Docker Compose e Nginx

## Execução local

### Backend

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements\dev.txt
cd backend
$env:DJANGO_SETTINGS_MODULE='config.settings.test'
..\.venv\Scripts\python.exe manage.py check
..\.venv\Scripts\python.exe manage.py migrate
..\.venv\Scripts\python.exe manage.py test
```

Para desenvolvimento normal, configure as variáveis a partir de `.env.example` e execute `manage.py runserver` com as configurações locais.

### Frontend

```powershell
cd frontend
npm.cmd ci
npm.cmd test
npm.cmd run build
npm.cmd run dev
```

Defina `VITE_API_URL` quando a API não estiver em `http://127.0.0.1:8000/api`.

### Docker

```powershell
docker compose config --quiet
docker compose up --build
```

Frontend: `http://127.0.0.1:5173`  
Backend: `http://127.0.0.1:8000/api/health/`

## Documentação

- [Arquitetura](ARCHITECTURE.md)
- [Roadmap](ROADMAP.md)
- [Controle multiusuário](docs/SEGURANCA-MULTIUSUARIO.md)
- [Produção integrada](docs/PRODUCAO-INTEGRADA.md)
- [Índice das Sprints](documentos/SPRINTS.md)
- [Documentação das APIs](docs/api/README.md)
- [Prompt Mestre](docs/PROMPT-MESTRE-AGRO-AI-PRO.md)
