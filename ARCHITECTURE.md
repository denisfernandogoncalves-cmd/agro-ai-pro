# Arquitetura do AGRO-AI-PRO

## Visão geral

O AGRO-AI-PRO é um ERP agrícola modular, estruturado em camadas para evolução
incremental, preservação de contratos e isolamento por propriedade.

## Componentes principais

- Backend: Django 5 + Django REST Framework
- Autenticação: JWT com Simple JWT
- Frontend: React 19 + Vite + TypeScript
- Mapas: React Leaflet + OpenStreetMap
- Banco de dados: PostgreSQL 17
- Testes locais: SQLite em memória
- Infraestrutura: Docker Compose e Redis; Nginx preparado para evolução

## Estrutura

- `backend/`: aplicação Django principal;
- `frontend/`: aplicação React principal;
- `docker/`: arquivos de containerização;
- `docs/`: documentação técnica e de produto;
- `database/`: persistência e dumps;
- `backups/`: backups e exportações.

## Segurança e escopo

A API usa autenticação por padrão. A camada multiusuário filtra querysets por
propriedade antes da busca por identificador, retornando HTTP 404 para objetos
externos ao escopo e HTTP 403 para ações incompatíveis com o papel. A interface
reflete permissões, mas não substitui a proteção do backend.

Papéis suportados:

- administrador;
- gestor;
- operador;
- somente leitura;
- superusuário Django com acesso completo.

## Frontend Enterprise

A primeira entrega da modernização introduz:

- shell responsivo com sidebar fixa, recolhível e drawer móvel;
- cabeçalho contextual por propriedade e safra;
- Dashboard Executivo usando apenas APIs existentes;
- design tokens e temas claro/escuro;
- componentes compartilhados;
- mapa agrícola consolidado;
- módulos carregados sob demanda com `React.lazy` e `Suspense`;
- preservação dos módulos legados e de suas regras de permissão.

## Contextos de negócio

### Propriedades, Talhões e Geoprocessamento

Propriedades e talhões são as referências territoriais. KML é validado no
backend, persistido como GeoJSON e apresentado no mapa.

### Estoque

O contexto atual de Estoque controla insumos, defensivos, fertilizantes,
sementes, lotes, validade e movimentações utilizadas nas operações de campo.

### Operações

O app existente `apps.producao` implementa operações agrícolas por talhão:
preparo, plantio, adubação, pulverização, irrigação, colheita, custos e consumo
de insumos. Seu nome técnico e suas APIs serão preservados por compatibilidade.

### Gestão da Produção Agrícola

O novo contexto oficial será implementado separadamente, planejado como
`apps.gestao_producao`. Ele cobrirá:

- múltiplos CAD/PRO por propriedade;
- recebimentos e qualidade;
- estoque físico de grãos;
- locais e transferências;
- contratos, terceiros e notas fiscais;
- embarques e integração financeira;
- auditoria, relatórios, mapa e insights.

Essa separação impede que estoque de insumos, operações de campo e estoque
comercial de grãos compartilhem regras incompatíveis. As entidades existentes
serão referenciadas por chave estrangeira sempre que possível, sem duplicação de
propriedades, talhões, parceiros ou lançamentos financeiros.

A especificação completa está em
[`docs/MODULO-GESTAO-PRODUCAO.md`](docs/MODULO-GESTAO-PRODUCAO.md).

## Decisões de integridade

- propriedades com talhões usam `PROTECT`;
- exclusões protegidas retornam conflito em vez de apagar dados em cascata;
- movimentos físicos ou financeiros confirmados devem ser corrigidos por
  estorno, não por edição destrutiva;
- operações que alteram múltiplos saldos devem ser atômicas;
- dados exibidos em dashboards devem vir de APIs reais ou de estados vazios
  explícitos, nunca de valores simulados;
- integrações externas pagas não são necessárias para a arquitetura atual.

## Testes

`config/settings/test.py` usa SQLite em memória para tornar a suíte reproduzível.
A CI executa Django Check, verificação de migrations, testes backend, testes e
build frontend, Docker Compose, `git diff --check` e verificação básica de
credenciais versionadas.
