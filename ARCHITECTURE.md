# Arquitetura do AGRO-AI-PRO

Este é o documento arquitetural canônico do projeto. Documentos históricos em
`01-Arquitetura/` e `03-Arquitetura/` devem apenas apontar para este arquivo e
não definir tecnologias ou decisões divergentes.

## Estado da solução

O AGRO-AI-PRO é um ERP agrícola modular com API Django REST Framework e
interface React/TypeScript. A versão 1.0 é funcional, mas a prontidão para
produção depende da conclusão da auditoria registrada em `docs/auditoria/`.

## Componentes principais

- **Backend:** Django 5 e Django REST Framework.
- **Autenticação:** JWT com Simple JWT.
- **Frontend:** React 19, Vite e TypeScript.
- **Aplicativo:** PWA produzida pelo mesmo frontend React.
- **Mapas:** React Leaflet e OpenStreetMap.
- **Banco de dados:** PostgreSQL 17 em desenvolvimento e produção.
- **Testes locais:** SQLite em memória quando o teste não exige recursos
  específicos do PostgreSQL.
- **Infraestrutura:** Docker Compose, Redis e preparação para proxy reverso.

React Native não faz parte da arquitetura implementada da versão 1.0. Uma
aplicação móvel nativa somente deve ser adicionada após decisão arquitetural e
entrada explícita no roadmap.

## Estrutura do repositório

- `backend/`: aplicação Django, módulos de domínio, API e testes.
- `frontend/`: aplicação React, PWA, componentes e integração com a API.
- `docker/`: arquivos auxiliares de containerização.
- `docs/`: documentação técnica, requisitos, API, Sprints e auditorias.
- `documentos/SPRINTS.md`: índice operacional canônico das Sprints.
- `database/`: documentação e artefatos auxiliares; migrations pertencem aos
  apps Django.
- `scripts/`: automações de desenvolvimento e validação.

## Limites e dependências

Cada app Django representa um domínio de negócio. Views e serializers devem
orquestrar entrada e saída; regras transacionais relevantes devem permanecer
em serviços de domínio. Consultas reutilizadas e complexas podem ser isoladas
em selectors ou QuerySets, sem criar uma camada de repositório genérica sobre
o ORM do Django.

O frontend acessa o backend exclusivamente pela API. Segredos, credenciais e
regras de autorização nunca devem ser confiados ao cliente.

## Decisões vigentes

- A API exige autenticação por padrão para evitar exposição acidental.
- Propriedades com talhões vinculados usam integridade referencial protegida;
  exclusões inválidas retornam conflito em vez de apagar dados em cascata.
- O processamento KML atual prioriza validação segura, preservação de Polygon e
  MultiPolygon e cálculo geodésico aproximado documentado.
- `config/settings/test.py` usa SQLite em memória para manter a suíte básica
  reproduzível sem PostgreSQL.
- O aplicativo entregue na versão 1.0 é uma PWA; suporte nativo é evolução
  futura, não requisito concluído.

## Governança arquitetural

Mudanças de tecnologia, fronteiras de domínio, persistência, autenticação ou
estratégia de aplicativo devem ser registradas como decisão em
`docs/decisoes/` e refletidas neste documento. O código executável é a evidência
final; documentos de Sprint não podem declarar prontidão superior à validada
por testes e pela auditoria.
