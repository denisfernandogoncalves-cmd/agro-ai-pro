# Changelog

## Em desenvolvimento — evolução Enterprise

### Segurança

- adiciona controle multiusuário por propriedade;
- cria papéis de administrador, gestor, operador e somente leitura;
- isola consultas, filtros, relatórios e insights por usuário;
- bloqueia acesso direto a IDs de outras propriedades com HTTP 404;
- preserva superusuários com acesso completo;
- adiciona autorização por CAD/PRO;
- oculta ações incompatíveis no frontend, mantendo a proteção principal no backend.

### Interface

- substitui a navegação horizontal por shell Enterprise com sidebar responsiva;
- adiciona Dashboard Executivo, contexto de propriedade e safra e identificação do usuário;
- adiciona design tokens, temas claro/escuro e preferência persistida;
- adiciona componentes compartilhados de tabela, cartões, filtros e estados de carregamento;
- adiciona carregamento sob demanda dos módulos;
- consolida o mapa agrícola para propriedades e talhões;
- preserva todas as telas e operações existentes.

### Gestão Integrada da Produção Agrícola

- adiciona culturas, safras e múltiplos CAD/PRO;
- adiciona motoristas, veículos e terceiros integrados aos parceiros financeiros;
- registra recebimentos com pesos, sacas, umidade, impureza e defeitos;
- adiciona estoque de grãos por propriedade, CAD/PRO, talhão, cultura, safra e armazenagem;
- implementa entradas, saídas, transferências, ajustes e estornos sem saldo negativo;
- adiciona contratos e embarques;
- cria contas a receber automaticamente após embarques confirmados;
- adiciona auditoria imutável;
- adiciona Dashboard de produção, qualidade, estoque, contratos, embarques e receita;
- adiciona relatórios JSON, CSV, Excel e PDF;
- adiciona importação assistida de CSV, XLSX e XLSM;
- amplia o assistente com comparativo entre safras, produtividade, qualidade, estoque e cobertura contratual;
- adiciona testes de autorização, estoque, recebimento, transferência e integração financeira.

### Correções da versão 1.0

- corrige o isolamento dos indicadores de estoque por propriedade e safra;
- corrige os alertas de estoque do assistente gerencial;
- valida filtros de propriedade e evita erro interno com parâmetros inválidos;
- corrige a contagem de propriedades inexistentes no dashboard;
- reduz consultas repetidas no cálculo da posição de estoque;
- adiciona renovação automática do token JWT no frontend;
- adiciona testes de regressão para filtros, consultas e sessão.

## Versão 1.0

- conclusão das Sprints 1 a 12;
- homologação do backend, frontend, PWA e ambiente Docker.
