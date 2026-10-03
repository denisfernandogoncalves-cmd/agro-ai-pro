# Administração de usuários e acessos por módulo

## Escopo e critérios de aceite

Solicitação do Product Owner: editar e excluir usuários e definir os itens permitidos. Incremento da infraestrutura/autenticação (nenhuma Sprint numerada está pendente nos índices). Critérios: administração exclusiva de administradores; edição de identificação, e-mail, status e senha opcional; exclusão preservando históricos; seleção dos 17 módulos do menu; bloqueio das APIs sem depender do menu; compatibilidade das contas atuais; migration aditiva, testes e entrega local.

Branch: `codex/propriedades-impressao-a4-20260921`, checkout de execução `.worktrees/runtime-origin-main`. Alterações locais anteriores preservadas. Sem commit, push ou merge.

## Implementação e decisão

`AcessoUsuario` possui vínculo único com o usuário, lista JSON de módulos e data de exclusão lógica. Ausência de configuração mantém os acessos anteriores. Administradores possuem todos os módulos e gestão de usuários; não é possível promover uma conta pela API de usuários. Superadministradores só podem ser alterados por outro superadministrador. Não é possível desativar/excluir a própria conta ou deixar o sistema sem administrador ativo. Atualizações/exclusões usam transações e bloqueios dos usuários para preservar essas garantias. Eventos registram IDs, sem senhas ou tokens.

Excluir desativa o login e retira a conta da lista sem apagar o registro ou seus vínculos. Access/refresh anteriores não autenticam contas inativas. O nome de usuário permanece reservado. Não há restauração da exclusão pela interface. Desativação pelo campo Ativo é reversível na edição.

A seleção concede consulta e uso do módulo, sem separar leitura/escrita nem restringir propriedades específicas. Relatórios e Assistente autorizam suas informações consolidadas. Catálogos consultados para preencher os módulos são compartilhados em leitura; isso não autoriza alterar seus cadastros. Exemplo: Cargas pode consultar propriedades, CAD/PRO, armazéns, talhões e grupos, mas só lançar/editar cargas.

A autorização central é executada em `AcessoJWTAuthentication`, derivada da autenticação existente. Essa posição protege também views que declaram suas próprias permissões DRF. Conta e configuração são consultadas em cada chamada, portanto um JWT já emitido obedece às novas restrições imediatamente. Não foi alterado o mecanismo de emissão/refresh. Views de usuários mantêm `IsAdminUser`. Testes de autorização usam JWT real (force_authenticate ignora autenticação por definição). Novos caminhos de API privada devem ser incluídos explicitamente nas regras; caminhos desconhecidos são negados para contas comuns.

O frontend espera `/auth/me/` antes de renderizar dados, exibe só módulos permitidos e escolhe o primeiro disponível. Sem módulos, apresenta mensagem para solicitar acesso. Permissões são atualizadas ao focar a janela e a cada 30 segundos; no backend a restrição é imediata. Edição permite manter a senha atual deixando os campos vazios. Exclusão solicita confirmação com a informação de que o histórico será preservado.

## APIs

- `GET/POST /api/auth/users/`: lista/criação para administradores, incluindo `modulos` e `is_active`.
- `GET/PATCH/DELETE /api/auth/users/<id>/`: detalhe, edição parcial e exclusão lógica para administradores.
- `GET /api/auth/me/`: retorna `id`, `username`, `is_staff`, `modulos` da conta autenticada.
- `modulos`: lista de IDs de módulos do menu. Lista vazia nega todos; IDs desconhecidos retornam 400. Administradores mantêm a lista completa.
- Senhas continuam write-only, validadas e armazenadas por hash. PATCH sem senha preserva o hash. `is_staff` é somente leitura e `is_superuser` não é aceito como campo de escrita.

## Arquivos e migration

Backend: `apps/accounts/models.py`, `access.py`, `users.py`, `urls.py`, `test_user_access.py`, `migrations/0001_initial.py`, `apps/core/middleware.py` e `config/settings/base.py`.
Frontend: `src/api/usuarios.ts`, `src/components/NavegacaoModulos.tsx`, `src/pages/Usuarios/UsuariosPage.tsx`, `src/App.tsx`, `src/styles.css` e `scripts/test-components.mjs`.

Migration `accounts.0001_initial` aplicada no banco local após plano confirmar apenas a nova tabela. Não altera os usuários existentes, senhas ou permissões já cadastradas. Nenhum usuário real foi editado, excluído ou criado durante a validação.

## Backup

`backups/sincronizacao-20261001-131318`: código dos 13 worktrees incluindo alterações locais, uploads, manifesto por arquivo com hashes, Git bundle verificado e ZIPs validados. Banco em `postgres.dump`; novo dump imediatamente antes da migration em `postgres-pre-migration.dump`, validado com `pg_restore --list` (613 linhas). SHA-256 registrado em `manifesto-dump.json` e `manifesto-pre-migration.json`.

## Validações e limitações

- `python manage.py test apps.accounts apps.core --noinput`: 41 testes aprovados no PostgreSQL isolado, incluindo autenticação concorrente, acesso direto via JWT, edição sem trocar senha, módulos desconhecidos, restrições de transferências, dependências de consulta, exclusão e bloqueio de tokens anteriores.
- `python manage.py test apps.accounts --settings=config.settings.test --noinput`: 35 testes na primeira validação direcionada; 33 aprovados e 2 concorrentes ignorados em SQLite. Em seguida foram adicionados dois cenários de acesso e validados no PostgreSQL acima.
- `npm.cmd --prefix frontend test`: aprovado, incluindo seleção de módulos no menu, menu vazio, todos os módulos para administrador, formulário de 17 acessos e 13 cenários de autenticação.
- `npm.cmd --prefix frontend run build` e Docker build do frontend: aprovados. Aviso de bundle acima de 500 kB permanece.
- `python manage.py check`, `makemigrations --check --dry-run`, `migrate --check` e `git diff --check`: aprovados.
- Suíte completa SQLite: 500 testes, 39 ignorados, 2 falhas e 2 erros fora da alteração de usuários. Testes `apps.estoque.test_compras.CompraEstoqueTests.test_lista_busca_e_imutabilidade` e `apps.estoque.tests.EstoqueApiTests.test_movimentos_sao_imutaveis` esperam DELETE 405, enquanto a implementação existente permite 204. Testes históricos `apps.graos.test_migration_0006` e `test_migration_0009` usam estado antigo de Propriedade enquanto a tabela já possui `bp_cvale` obrigatório. Esses quatro testes não verificam a autorização JWT introduzida e exigem atualização separada das expectativas/estados de migration.
- Interface verificada por renderização estática de componentes e testes; navegação visual autenticada e edição de usuários reais não executadas. Serviços locais e entrega dos novos assets verificados após atualização.
- Conferência final somente de leitura: 3 contas preservadas, nenhuma configuração de acesso criada para usuários reais e nenhuma senha exposta pela serialização. Frontend/backend/PostgreSQL/Redis saudáveis; página, API de saúde e novos assets respondendo HTTP 200 na porta 5174. Nenhuma migration pendente ou alteração de modelo sem migration.

## Uso

Atualizar a página com Ctrl+F5, entrar como administrador e abrir Usuários. Clicar Editar no usuário, marcar/desmarcar Itens permitidos e Salvar alterações. Excluir pede confirmação e preserva os lançamentos anteriores.

## Auditoria posterior

A auditoria posterior corrigiu a renovação de sessão na consulta de acessos, revalidou administradores durante mutações concorrentes e ajustou os quatro testes antigos citados acima. A suíte completa passou (501 testes, 39 ignorados); detalhes e recomendações de telas em `2026-10-01-auditoria-telas-usuarios.md`.
