# Changelog

## Em desenvolvimento — manutenção da versão 1.0

- adiciona logout JWT idempotente com blacklist oficial do Simple JWT;
- reduz o access token para 15 minutos e habilita rotação segura do refresh;
- protege autenticação e APIs privadas contra armazenamento em cache;
- adapta o PWA ao novo refresh rotacionado e ao logout remoto;
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
