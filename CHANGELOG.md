# Changelog

## Em desenvolvimento — versão 1.1

- adiciona Gestão Integrada da Produção Agrícola;
- permite múltiplos CAD/PRO por propriedade e acesso adicional por CAD/PRO;
- adiciona culturas, safras, motoristas, veículos e contratos;
- registra recebimentos, peso, qualidade e local de armazenagem;
- controla saldo de grãos por propriedade, CAD/PRO, talhão, cultura, safra e local;
- adiciona entradas, saídas, transferências, ajustes e estornos transacionais;
- bloqueia estoque negativo no serviço e no banco;
- adiciona embarques com validação de contrato, baixa de estoque e receita financeira;
- mantém movimentações e auditorias imutáveis;
- adiciona dashboard e relatórios JSON, CSV, XLSX e PDF;
- adiciona importação CSV/XLSX/XLSM com detecção de colunas, prévia e confirmação;
- integra insights explicáveis de produção, produtividade, estoque, qualidade e contratos;
- ativa shell Enterprise, sidebar responsiva, temas e carregamento sob demanda;
- adiciona testes de saldo, permissões, integração financeira, importação e exportações;
- não utiliza serviço pago, telemetria ou processamento externo de arquivos.

## Em desenvolvimento — manutenção da versão 1.0

- adiciona controle multiusuário por propriedade;
- cria papéis de administrador, gestor, operador e somente leitura;
- isola consultas, filtros, relatórios e insights por usuário;
- bloqueia acesso direto a IDs de outras propriedades;
- preserva superusuários com acesso completo;
- inclui migration segura e vinculação automática de superusuários;
- oculta ações não permitidas na tela de propriedades;
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
