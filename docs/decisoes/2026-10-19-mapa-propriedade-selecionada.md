# Mapa abaixo da propriedade selecionada

Nome da propriedade vira um botão acessível, acionável por clique/teclado, com estado expandido. Abre o mapa imediatamente dentro do cadastro selecionado, abaixo dos dados e ações; clicar novamente no nome fecha. Selecionar outra propriedade troca o mapa. Edição e exclusão preservadas. Lista não abre automaticamente o primeiro mapa.

Reutilizado MapaPropriedade, com satélite/mapa convencional, marcador e geometria existente. A causa dos mapas ausentes em GMS era a condição anterior, que exigia latitude/longitude decimais. Coordenadas GMS são convertidas para exibição pelo conversor existente, sem modificar os dados originais. Decimais, vírgula decimal e ponto zero aceitos; coordenadas ausentes/inválidas não apontam para zero e exibem aviso para editar o cadastro.

Backup anterior: `D:/PROJETOS/AGRO-AI-PRO/backups/visual-20261019-221834`, código, banco e uploads verificados. Testes frontend, coordenadas e autenticação aprovados; TypeScript/Vite e diff conferidos. O carregamento das imagens depende dos provedores de mapa já existentes. Sem migrations ou alterações persistentes. Conferência visual no navegador não executada.

Revisão: segundo clique também no cartão fecha o mapa, usando a mesma alternância do nome. Cliques dentro do mapa, Editar e Excluir continuam sem alternar a seleção. Backup anterior: `D:/PROJETOS/AGRO-AI-PRO/backups/visual-20261019-222155`.
