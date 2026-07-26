# Changelog

## Em desenvolvimento — manutenção da versão 1.0

- inicia a primeira entrega da interface Enterprise com shell responsivo, sidebar, Dashboard Executivo, temas e design tokens;
- adiciona carregamento sob demanda dos módulos e componentes compartilhados;
- consolida o mapa agrícola com propriedades, talhões, legenda, escala e suporte a novas camadas;
- registra Gestão da Produção Agrícola como módulo oficial pós-1.0;
- prepara a navegação e as camadas de mapa para Produção e locais de armazenagem, sem criar dados simulados;
- documenta a separação entre Operações de campo, estoque de insumos e estoque físico de grãos;
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
