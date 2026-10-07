# Usuários e limpeza local — 27/09/2026

## Escopo e aceite

Pedido do Product Owner: limpar todos os cadastros e lançamentos, preservando
usuários e senhas, e disponibilizar uma tela para criar usuários e senhas.
Entrega aplicada à cópia que atende http://127.0.0.1:5174/:
`D:/PROJETOS/AGRO-AI-PRO/.worktrees/runtime-origin-main`, branch
`codex/propriedades-impressao-a4-20260921`. Alterações locais anteriores preservadas.

Critérios atendidos: dados dos módulos zerados; contas e hashes de senha
idênticos antes/depois; criação de usuário restrita a administradores;
confirmação e validação de senha; senha armazenada pelo hash do Django;
novo usuário consegue autenticar e não recebe privilégios administrativos.

## Implementação

- `backend/apps/accounts/users.py`: serialização, listagem/criação e identificação da conta atual.
- `backend/apps/accounts/urls.py`: GET `/api/auth/me/` e GET/POST `/api/auth/users/`.
- `backend/apps/accounts/test_users.py`: autorização, validação, hash, login e proteção de privilégios.
- `frontend/src/pages/Usuarios/UsuariosPage.tsx`: formulário, confirmação, estados de envio e listagem.
- `frontend/src/App.tsx`: menu Usuários para administradores.
- `frontend/scripts/test-auth.mjs`: adaptação do mock da API da aplicação.

POST aceita username, first_name, last_name, email, password e
password_confirmation. Retorna 201 com dados públicos da conta. Senhas são
write-only. Campos administrativos não são graváveis. Contas comuns recebem
403; acesso anônimo recebe 401. Senhas exigem oito caracteres e os validadores
de similaridade, senhas comuns e conteúdo exclusivamente numérico do Django.
Novas contas têm o acesso operacional já definido pelo aplicativo; esta entrega
não implementa permissões por módulo nem edição/reset de senhas existentes.
Não houve mudança de modelos, dependências ou migrations nesta tarefa.

## Backup e limpeza

Backups privados, ignorados pelo Git, em `D:/PROJETOS/AGRO-AI-PRO/backups/`:

- `agro-ai-pro-2026-09-27-135714-885931`: código com alterações locais, uploads e cópia física do PostgreSQL parado.
- `agro-ai-pro-2026-09-27-135934-380937`: código, uploads e pg_dump imediatamente anterior à limpeza.

Manifestos registram SHA-256. ZIPs tiveram CRC validado; o arquivo físico foi
lido integralmente e o dump lógico validado por pg_restore sem restauração.
Foram limpas 44 tabelas de domínio, incluindo vínculos automáticos: 458 registros.
TRUNCATE transacional sem CASCADE, com bloqueio e comparação integral das duas
contas antes/depois. Auth, permissões, sessões e migrations foram preservados.
Uploads antigos foram movidos para `backups/limpeza-20260927/uploads-arquivados`
na cópia de execução, fora do MEDIA_ROOT público. Contagens e script da operação
ficam em `backups/limpeza-20260927/resultado.json` e `executar.py`.
Nenhuma conta de teste foi adicionada ao banco real.

## Verificação

Na cópia de execução, com Docker Compose `-p agro-ai-pro`:

- `exec -T backend python backend/manage.py test apps.accounts --noinput`: 19 testes aprovados em PostgreSQL isolado.
- `exec -T backend python backend/manage.py check`: sem problemas.
- `exec -T backend python backend/manage.py makemigrations --check --dry-run`: nenhuma alteração.
- `npm.cmd run build`: aprovado; aviso de bundle acima de 500 kB.
- `npm.cmd test`: componentes e 13 cenários de autenticação aprovados.
- `docker compose -p agro-ai-pro build frontend`: aprovado; frontend recriado com FRONTEND_PORT=5174.
- `exec -T -w /app/backend backend python manage.py test --settings=config.settings.test --noinput`: 431 testes, 393 aprovados, 36 ignorados e 2 falhas no Estoque.
- `git diff --check`: aprovado.
- Navegador: propriedades vazias, menu Usuários, formulário e duas contas administradoras visíveis.
- Backend, frontend, PostgreSQL e Redis saudáveis após atualização.

As duas falhas gerais são `test_lista_busca_e_imutabilidade` e
`test_movimentos_sao_imutaveis`: esperam DELETE 405, mas obtêm 204. As views e
services do Estoque já tinham alterações locais de exclusão antes desta tarefa;
nenhum arquivo do Estoque foi modificado aqui. A suíte global permanece com essa
pendência, sem impedir os testes específicos de usuários aprovados.

Nenhuma Sprint anterior teve seu status alterado. Sem commit, push ou merge.
