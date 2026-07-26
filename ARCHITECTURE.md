# Arquitetura do AGRO-AI-PRO

## Visão geral

O AGRO-AI-PRO é um ERP agrícola modular, com backend orientado a domínios e frontend React carregado sob demanda. A evolução preserva contratos existentes e integra novos fluxos por serviços transacionais compartilhados.

## Componentes principais

- Backend: Django 5 + Django REST Framework.
- Autenticação: JWT com Simple JWT e renovação automática no frontend.
- Autorização: papéis por propriedade e escopo adicional por CAD/PRO.
- Frontend: React 19 + Vite + TypeScript, shell Enterprise responsivo.
- Mapas: React Leaflet + OpenStreetMap, sem serviço pago.
- Banco de dados: PostgreSQL 17.
- Testes: SQLite em memória e PostgreSQL no ambiente Docker.
- Infraestrutura: Docker Compose, Redis e Nginx.

## Organização

- `backend/config/`: configurações e roteamento global.
- `backend/apps/`: domínios de negócio.
- `frontend/src/app/`: navegação e carregamento dos módulos.
- `frontend/src/components/`: componentes compartilhados, layout e mapas.
- `frontend/src/pages/`: telas organizadas por domínio.
- `docs/`: arquitetura, APIs, segurança, fluxos e operação.
- `database/`: persistência e procedimentos de banco.
- `backups/`: backups e exportações controladas.

## Domínios

### Estrutura territorial

`propriedades`, `talhoes` e geoprocessamento definem os limites de acesso, a origem dos dados agronômicos e as geometrias KML/GeoJSON.

### Operações agrícolas

`apps.producao.OperacaoAgricola` preserva o planejamento e a execução de atividades de campo, incluindo consumo transacional de insumos.

### Gestão integrada da produção

O mesmo app `producao` recebe um subdomínio separado para o fluxo pós-colheita:

- cadastros de cultura, safra, CAD/PRO, motorista e veículo;
- recebimentos e qualidade;
- saldos e movimentações de grãos;
- contratos e embarques;
- integração financeira;
- importação, relatórios e auditoria.

Os modelos residem em `grain_models.py`, serviços em `grain_services.py`, autorização em `grain_access.py`, importação em `grain_imports.py`, relatórios em `grain_reports.py` e APIs em `grain_views.py`. Os modelos são registrados pelo `models.py` do app para manter um único domínio Django e preservar as rotas existentes.

## Autorização

A proteção é aplicada no backend antes da localização dos objetos:

1. JWT autentica o usuário.
2. `AcessoPropriedade` define o papel na propriedade.
3. `AcessoCadPro` restringe os CAD/PRO visíveis.
4. querysets são filtrados pelo escopo autorizado.
5. IDs externos retornam HTTP 404.
6. papéis insuficientes retornam HTTP 403.

A interface usa os mesmos metadados para ocultar ações, mas nunca substitui a validação do backend.

## Transações e auditoria

Recebimentos, transferências, ajustes, embarques e estornos usam `transaction.atomic` e bloqueio de saldos com `select_for_update`. O banco possui restrição de saldo não negativo. Movimentações confirmadas são imutáveis; correções geram registros inversos.

A confirmação de embarque valida o contrato, baixa o estoque, cria conta a receber e registra auditoria na mesma transação.

## Importação e exportação

O importador processa CSV, XLSX e XLSM localmente, com limite de tamanho, hash SHA-256, mapeamento, prévia e confirmação. XLSX/XLSM usam `openpyxl` e `defusedxml`. Exportações CSV, XLSX e PDF são produzidas no backend sem serviço externo.

## Frontend Enterprise

- `AppEnterprise` coordena autenticação, propriedades e contexto global.
- `AppShell` fornece sidebar, drawer móvel, cabeçalho e temas.
- `ModuleRenderer` aplica `React.lazy`, `Suspense` e boundary de erro.
- componentes compartilhados padronizam cards, tabelas, estados e permissões.
- design tokens centralizam cores, tipografia, espaços, bordas, sombras e estados.

## Decisões de segurança

- API autenticada por padrão.
- integridade referencial com `PROTECT` para registros operacionais.
- exclusões sensíveis retornam conflito em vez de apagar histórico.
- nenhuma credencial é versionada.
- planilhas e documentos não são enviados a terceiros.
- nenhuma API paga, analytics ou telemetria é utilizada.
- testes usam dados fictícios e banco isolado.
