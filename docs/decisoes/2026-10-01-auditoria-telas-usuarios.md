# Auditoria das telas e da administração de usuários — 01/10/2026

## Objetivo, método e alcance

Auditar telas, usabilidade e a implementação recente de usuários. Branch `codex/propriedades-impressao-a4-20260921`, checkout de execução `.worktrees/runtime-origin-main`. Leitura dos componentes dos 17 módulos, estilos, fluxo de autenticação e APIs; testes isolados; inspeção pelo navegador integrado na porta 5174. Preservadas alterações locais anteriores. Não houve edição de contas reais, exclusão de dados, mudança de senha ou alteração de permissões reais.

Backup antes das correções: `backups/sincronizacao-20261001-133920`, com código dos 13 worktrees, uploads, bundle/ZIPs verificados e manifestos de hashes. PostgreSQL em `postgres.dump`, validado com `pg_restore --list` (620 linhas) e SHA-256 em `manifesto-dump.json`.

## Problemas confirmados e corrigidos

| Prioridade | Achado | Correção e evidência |
| --- | --- | --- |
| Alta | Token vencido na consulta `/auth/me/` bloqueava a área privada. O interceptor excluía de renovação todo o prefixo `/auth/`, incluindo consulta de permissões e gestão de contas. | Restrição agora se aplica somente a emissão, refresh e logout. Consultas de usuários e acessos renovam normalmente. Teste comportamental de ambas as rotas passou, preservando os testes contra renovação após logout. No navegador, a sessão antiga deixou de ficar presa na tela de erro e voltou ao login quando não pôde ser renovada. |
| Alta | Administrador autenticado antes de uma desativação concorrente ainda podia criar/editar/excluir usuários usando o objeto anterior à mudança. | Revalidação do administrador dentro da transação, após os bloqueios, em todas as mutações de contas. Conta desativada, removida ou sem status administrador recebe 403. Teste confirma ausência de alterações quando a autenticação é anterior à revogação. |
| Média | Mensagens de erro/sucesso em vários módulos não possuíam semântica para anúncio por leitores de tela. | Adicionados `role="alert"` a erros e `role="status"` a sucessos nos elementos sem essas marcações. Sem modificar o layout ou as regras de negócio. |
| Alta | Em 360 px, Produção e saldos alcançava 1.169 px de largura e Vendas 884 px, ultrapassando a página. | Grades de módulo e detalhe de venda usam colunas `minmax(0, 1fr)`; filhos podem encolher; campos da venda deixam de criar colunas implícitas no celular. Tabelas conservam rolagem própria. |
| Média | Quatro testes gerais tinham expectativas/estados incompatíveis com funcionalidades já presentes. | Dois testes de estoque passam a validar a exclusão controlada existente (204), registros removidos e saldo zero; continuam rejeitando PATCH. Dois testes históricos de grãos usam o estado de Propriedade correspondente ao campo BP já presente no banco de testes. Não houve alteração das migrations aplicadas ou das regras de exclusão do estoque. |

## Melhorias recomendadas para as telas

Estas são recomendações de interface, não uma reformulação já implementada. As evidências vêm do código, dos cartões enviados e da navegação autenticada nos 17 módulos e Usuários, em larguras de computador e celular. Não foram submetidos formulários de negócio ou realizadas transações reais. O menu extenso e os formulários antes das listas foram confirmados na interface.

| Tela | Prioridade | Próxima melhoria concreta | Evidência / motivo |
| --- | --- | --- | --- |
| Navegação geral | Alta | Agrupar módulos em Cadastros, Produção, Comercial, Financeiro e Administração; manter o módulo atual destacado. | Menu reúne 17 módulos e Usuários em botões. Muitos itens competem pela atenção. |
| Propriedades | Média | Exibir primeiro busca/lista e abrir cadastro/edição ao acionar Novo/Editar; levar foco ao formulário em edição. | Formulário e lista ficam simultaneamente na grade da página principal. |
| Talhões | Média | Tornar a edição e o histórico do talhão selecionado mais evidentes, com título/foco e retorno claro à lista. | Fluxo dividido entre formulário, lista, grupos e histórico. |
| Cadastros agrícolas | Média | Organizar os quatro tipos em abas ou seções recolhíveis, mantendo busca por tipo. | Armazéns, depósitos, produtos e fornecedores têm cadastro/lista na mesma página. |
| Cargas colhidas | Alta | Elevar textos secundários para cerca de 14 px e os botões de ação para área de toque de pelo menos 44 px no celular; mostrar datas em DD/MM/AAAA. | CSS usa .7/.75 rem em metadados e .8 rem nos botões; data no cartão aparece em ISO, enquanto a impressão já usa formato local. Preservar quebra automática e quantidades visíveis. |
| Produção e saldos | Média | Destacar saldo disponível e organizar a rastreabilidade em seção separada, com filtros resumidos no cabeçalho. | Há consolidado, posições detalhadas e movimentos recentes na mesma página. |
| Transferência de saldo | Alta | Reforçar visualmente origem → destino e o resumo de kg antes de confirmar. | Operação afeta duas posições; a identidade dos CAD/PROs precisa ser inequívoca. |
| Vendas | Alta | Separar visualmente identificação, transporte e quantidade; destacar o rateio na venda PARTICULAR e o resultado da saída. | Muitos campos e estados comerciais coexistem. Evitar comprimir todos os textos em um único bloco. |
| Clima | Média | Exibir claramente carregamento, data da última atualização e se os dados são armazenados ou recém-consultados. | Tela diferencia consulta e atualização, mas os estados de operação podem ficar mais evidentes. |
| Mercado | Média | Destacar unidade/moeda, origem e horário de cada cotação; manter notícias e clima em seções próprias. | Dados de naturezas diferentes aparecem na mesma tela. |
| Financeiro | Alta | Separar filtros usuais dos avançados e manter totais/pago/pendente visíveis sem competir com o cadastro de boleto. | Filtros incluem destinatário, parceiro, tipo, situação e datas; formulário e consulta extensos. |
| Estoque | Alta | Uniformizar fornecedor, produto, embalagem e unidade nos resumos; separar saldo atual de histórico de movimentos. | A mesma página combina compras, lotes, disponibilidade e rastreabilidade. |
| Operações | Média | Usar estados visuais Planejada/Em andamento/Concluída/Cancelada e resumo de insumos antes da execução. | Ações diferentes dependem do estado da operação selecionada. |
| Máquinas | Alta | Bloquear submissões repetidas durante gravação e dar mensagens específicas para frota/manutenções vazias. | Botões Cadastrar máquina/Salvar registro não estão ligados a estado de salvamento; listas usam map sem alternativa explícita quando vazias. Risco de duplicar registros por cliques repetidos precisa ser tratado no fluxo/API. |
| Faturamento de insumos | Média | Destacar sugestão versus quantidade manual e total a enviar; assegurar que a tabela role apenas dentro de seu contêiner no celular. | Tabela possui vários campos editáveis e exige comparar sugestão, embalagens e área. |
| Relatórios | Alta | Apresentar resumo dos filtros aplicados, período e total de registros junto ao resultado; tornar filtros avançados opcionais. | Formulário possui numerosos seletores além de catálogo de relatórios e paginação. |
| Assistente | Média | Mostrar estado de análise, bloquear acionamento repetido e distinguir “nenhum alerta” de “ainda não analisado”. | Não há estado de carregamento no componente; lista vazia usa somente map. |
| Usuários | Alta | Buscar usuários por nome/login, agrupar permissões por área e dar foco ao formulário ao editar. | Lista não possui busca; seleção contém 17 opções. Manter a explicação de que administradores têm acesso completo e a exclusão preserva histórico. |

## Sequência sugerida

1. Padronizar legibilidade, datas e área de toque das ações compactas.
2. Simplificar navegação e filtros, preservando as informações e os fluxos existentes.
3. Melhorar estados de carregamento/vazio e prevenção de envio repetido, começando por Máquinas e Assistente.
4. Validar larguras 360/768/1366 px, teclado, zoom e impressão de cada módulo com uma sessão autorizada.

## Validação técnica

- Suíte completa SQLite: 501 testes, 462 executados com sucesso, 39 ignorados por dependerem do PostgreSQL; zero falhas/erros. Log de falha simulada de importação é esperado pelo teste de rollback.
- PostgreSQL: 67 testes de accounts/core, migrations históricas de grãos e estoque aprovados. Revalidação final de accounts/core: 42 testes aprovados após refinamento defensivo para administrador removido.
- Frontend: componentes e 14 cenários comportamentais de autenticação aprovados; build aprovado. Aviso de bundle acima de 500 kB permanece como oportunidade de dividir o carregamento por módulo.
- Sem alterações de models/migrations nesta auditoria. Verificações de Django, consistência de migrations e diff executadas.
- Correções de autenticação e acessibilidade entregues no frontend local; backend usa o checkout montado. Não realizados commit, push ou merge.
- Reteste visual de Produção e saldos/Vendas: página 345 px em viewport de 360 px, 754 px em 768 px, e no máximo 1.366 px em 1.366 px. Códigos longos da rastreabilidade quebram linha; tabelas conservam rolagem interna. Frontend local respondeu HTTP 200 e contêiner saudável.

## Arquivos e comandos principais

- Segurança: `backend/apps/accounts/users.py` e `test_user_access.py`.
- Sessão: `frontend/src/api/propriedades.ts` e `frontend/scripts/test-auth.mjs`.
- Layout: `frontend/src/styles.css`; anúncios acessíveis em App e componentes de páginas.
- Testes históricos: `backend/apps/graos/test_migration_0006.py`, `test_migration_0009.py`, `backend/apps/estoque/test_compras.py` e `tests.py`.
- Validação: `python manage.py test --settings=config.settings.test --noinput`, testes PostgreSQL direcionados, `check`, `makemigrations --check --dry-run`, `migrate --check`, `npm.cmd --prefix frontend test`, `npm.cmd --prefix frontend run build` e `git diff --check`.
- Ambiente local: `docker compose -p agro-ai-pro build frontend` e atualização apenas do frontend, com porta 5174. Backup privado e mudanças anteriores preservados.

## Limites da auditoria

O usuário entrou diretamente no navegador integrado, sem compartilhar senha no chat. Foram abertas as telas internas e verificadas suas estruturas e larguras, sem erros visíveis nas consultas observadas. A auditoria não certifica todos os fluxos de gravação, a impressão física, navegação integral por teclado ou todos os tamanhos de tela. Troca de senha mantém a política atual de tokens de até 15 minutos; uma futura política de revogação de todas as sessões ao trocar senha deve ser definida antes de alterar esse comportamento.
