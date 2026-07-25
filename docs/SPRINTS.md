# Sprints — AGRO-AI-PRO

Este documento organiza a evolução do projeto. Uma Sprint somente deve ser marcada como concluída quando seus critérios de aceite forem atendidos e as verificações relevantes forem executadas.

## Legenda

- `[x]` concluído e validado
- `[~]` parcialmente implementado
- `[ ]` pendente
- `[!]` bloqueado

## Sprint 0 — Fundação do projeto

**Status:** `[~]`

### Objetivos

- estrutura Django modular;
- configuração por ambiente;
- PostgreSQL e Redis via Docker;
- autenticação e API base;
- documentação de instalação e operação;
- regras permanentes para agentes de IA;
- estratégia mínima de testes e integração contínua.

### Critérios de aceite

- [x] backend Django estruturado;
- [x] Docker Compose com PostgreSQL, Redis e backend;
- [x] Prompt Mestre documentado;
- [x] `AGENTS.md` criado;
- [x] exemplo de variáveis de ambiente disponível;
- [ ] README operacional validado em ambiente limpo;
- [ ] pipeline de integração contínua executando verificações essenciais;
- [ ] cobertura mínima de testes definida e documentada.

## Sprint 1 — Propriedades rurais

**Status:** `[~]`

### Objetivos

- cadastro completo de propriedades;
- API REST;
- coordenadas geográficas;
- upload de KML;
- validação de dados;
- testes do módulo.

### Critérios de aceite

- [x] model de propriedade criado;
- [x] campos básicos, área, município, UF e coordenadas;
- [x] campo para arquivo KML;
- [ ] validação formal de latitude, longitude, UF, área e extensão do arquivo;
- [ ] testes de model, serializer e endpoints;
- [ ] documentação da API;
- [ ] tratamento seguro de arquivos enviados.

## Sprint 2 — Talhões e geoprocessamento

**Status:** `[x]`

### Objetivos

- vincular talhões às propriedades;
- registrar cultura, safra e produtividade esperada;
- importar KML por talhão;
- preparar cálculo de centroide, área e indicadores topográficos.

### Critérios de aceite

- [x] model de talhão criado;
- [x] relacionamento com propriedade;
- [x] campos agronômicos básicos;
- [x] upload de KML;
- [x] validação de área do talhão contra área da propriedade;
- [x] processamento confiável do KML;
- [x] testes de API e regras de negócio;
- [x] perímetros preparados em GeoJSON para visualização no mapa.

## Sprint 3 — Clima por propriedade

**Status:** `[~]`

### Objetivos

- previsão do tempo por propriedade;
- histórico de consultas;
- alertas climáticos;
- armazenamento com origem e horário dos dados.

### Critérios de aceite

- [x] estrutura inicial do app de clima;
- [x] endpoint inicial de previsões;
- [ ] integração com provedor configurável;
- [ ] cache e política de atualização;
- [ ] testes;
- [ ] alertas por risco climático.

## Sprint 4 — Frontend operacional

**Status:** `[~]`

### Objetivos

- autenticação;
- dashboard;
- CRUD de propriedades e talhões;
- mapas;
- upload de KML;
- consumo seguro da API.

### Critérios de aceite

- [x] estrutura inicial do frontend;
- [x] componente inicial de mapa;
- [ ] fluxo de autenticação validado;
- [ ] telas completas de propriedades e talhões;
- [ ] tratamento de carregamento e erros;
- [ ] testes de componentes críticos;
- [ ] build de produção validado.

## Sprint 5 — Financeiro

**Status:** `[ ]`

- contas a pagar;
- contas a receber;
- categorias e centros de custo;
- leitura de código de barras;
- fluxo de caixa;
- relatórios e conciliação futura.

## Sprint 6 — Estoque e insumos

**Status:** `[ ]`

- produtos e unidades;
- entradas, saídas e ajustes;
- lançamentos com ou sem nota fiscal;
- lotes e validade;
- herbicidas, fungicidas, fertilizantes e demais insumos;
- custo médio e inventário.

## Sprint 7 — Produção agrícola

**Status:** `[ ]`

- culturas e safras;
- planejamento por talhão;
- operações agrícolas;
- produtividade estimada e realizada;
- média histórica por talhão;
- custos de produção.

## Sprint 8 — Mercado e Corn Belt

**Status:** `[ ]`

- soja, milho e trigo em Chicago;
- petróleo Brent;
- preços locais configuráveis;
- clima no Corn Belt;
- alertas e recomendações;
- histórico e rastreabilidade das fontes.

## Sprint 9 — Relatórios e inteligência

**Status:** `[ ]`

- dashboards gerenciais;
- relatórios em PDF e planilha;
- indicadores financeiros e produtivos;
- alertas inteligentes;
- apoio à tomada de decisão com explicações e fontes.

## Sprint 10 — Segurança, produção e nuvem

**Status:** `[ ]`

- configuração segura de produção;
- backups e restauração testados;
- observabilidade e logs;
- CI/CD;
- domínio, HTTPS e armazenamento de arquivos;
- política de permissões;
- publicação em nuvem.

## Regra de execução

Quando uma tarefa não indicar Sprint específica, o agente deve:

1. ler `AGENTS.md` e o Prompt Mestre;
2. identificar a primeira Sprint com pendência relacionada ao objetivo;
3. implementar uma entrega pequena, testável e reversível;
4. atualizar este documento somente com evidências;
5. abrir ou atualizar Pull Request;
6. nunca fazer merge sem aprovação explícita do Product Owner.
