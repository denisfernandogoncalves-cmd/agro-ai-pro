# Changelog

## Em desenvolvimento — manutenção da versão 1.0

- inicia a primeira entrega da interface enterprise em branch isolada;
- adiciona shell responsivo com sidebar fixa, recolhível e drawer móvel;
- adiciona Dashboard Executivo usando exclusivamente APIs existentes;
- centraliza design tokens e temas claro/escuro com preferência persistida;
- adiciona componentes compartilhados e carregamento sob demanda dos módulos;
- consolida mapas de propriedades e talhões com GeoJSON, marcadores, escala e legenda;
- preserva o controle multiusuário e os bloqueios visuais da PR #16;
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
