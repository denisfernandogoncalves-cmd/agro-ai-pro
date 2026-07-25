# Arquitetura do AGRO-AI-PRO

## Visão geral
O AGRO-AI-PRO será um ERP agrícola modular, estruturado em camadas bem definidas para evolução incremental.

## Componentes principais

- Backend: Django 5 + Django REST Framework
- Autenticação: JWT com Simple JWT
- Frontend: React 19 + Vite + TypeScript
- Mapas: React Leaflet + OpenStreetMap
- Banco de dados: PostgreSQL 17
- Testes locais: SQLite em memória
- Infraestrutura: Docker Compose e Redis; Nginx está preparado para evolução

## Estrutura proposta
- backend/: aplicação Django principal
- frontend/: aplicação React principal
- docker/: arquivos de containerização
- docs/: documentação técnica e de produto
- database/: persistência e dumps
- backups/: backups e exportações

## Decisões da Sprint 1

- A API usa autenticação por padrão para evitar exposição acidental de dados.
- Propriedades com talhões usam integridade referencial `PROTECT`; a exclusão
  retorna HTTP 409 em vez de apagar talhões em cascata.
- O parser KML usa apenas a biblioteca padrão do Python. Isso reduz dependências
  e atende à necessidade atual de validar o polígono e calcular o centroide.
- O arquivo `config/settings/test.py` usa SQLite em memória para tornar a suíte
  reproduzível sem depender do PostgreSQL de desenvolvimento.
