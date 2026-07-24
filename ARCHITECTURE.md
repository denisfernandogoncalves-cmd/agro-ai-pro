# Arquitetura do AGRO-AI-PRO

## Visão geral
O AGRO-AI-PRO será um ERP agrícola modular, estruturado em camadas bem definidas para evolução incremental.

## Componentes principais
- Backend: Django 5 + Django REST Framework
- Frontend: React 19 + Vite + TypeScript + Material UI
- Banco de dados: PostgreSQL 17
- Infraestrutura: Docker Compose, Redis e Nginx

## Estrutura proposta
- backend/: aplicação Django principal
- frontend/: aplicação React principal
- docker/: arquivos de containerização
- docs/: documentação técnica e de produto
- database/: persistência e dumps
- backups/: backups e exportações
