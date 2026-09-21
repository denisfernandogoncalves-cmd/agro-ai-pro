# Retomada de 12/09 — boleto unitário

Branch: `codex/grupos-propriedades-colheita`, checkout `.worktrees/runtime-origin-main`.
Alterações anteriores não commitadas foram preservadas.

## Objetivo e resultado

Conferir a correção interrompida em 12/09: salvar um único boleto com indicação
“1 de 4”, preservando valor, vencimento e código, e evitar sobreposição no
Financeiro. A implementação existente passou nas verificações desta retomada.
Documentação da API atualizada para distinguir o fluxo atual da API anterior
de parcelamento, preservada por compatibilidade.

## Backup

`backups/agro-ai-pro-2026-09-14-070549-042870`, dentro deste checkout.
Código incluindo alterações locais, uploads e cópia física do PostgreSQL
parado: 7216 entradas verificadas, cinco arquivos no manifesto.
Integridade: leitura integral do arquivo do banco, CRC dos ZIPs e hashes
SHA256 individuais registrados em `manifesto.json`. Sem restauração.

## Evidências

- Python do projeto, em `backend`: `manage.py test apps.financeiro apps.relatorios --settings=config.settings.test --noinput`: 58 testes aprovados.
- `manage.py makemigrations --check --dry-run --settings=config.settings.test`: sem alterações.
- Em `frontend`, `npm.cmd test`: 40 testes de componentes e 13 cenários de autenticação aprovados.
- `npm.cmd run build`: aprovado; aviso de bundle acima de 500 kB permanece.
- Docker: `docker compose -p agro-ai-pro exec -T -w /app/backend backend python manage.py check`: sem problemas.
- `showmigrations financeiro`: migrations 0001 a 0004 aplicadas. Nenhuma migration criada ou aplicada nesta retomada.
- `git -c core.safecrlf=false diff --check`: aprovado.
- Navegador real em `http://127.0.0.1:5174/`: acesso autenticado, módulo Financeiro aberto; mudar total para 4 exibiu “1 de 4”. Screenshot confirmou leitor, formulário e filtros separados, sem sobreposição na posição examinada.
- Nenhum boleto de teste foi salvo no banco do usuário; gravação e idempotência verificadas na suíte isolada.

## Ambiente e arquivos

Serviços estavam parados. Executado `docker compose -p agro-ai-pro start`.
O frontend iniciou antes de o backend estar disponível e encerrou por falha
de resolução do upstream. Após backend saudável, `start frontend` recuperou
o acesso. Não houve alteração da configuração Docker nesta retomada.

Arquivos alterados nesta retomada: `docs/api/FINANCEIRO.md` e este relatório.
Código validado: models, serializers, views, parcelamentos e teste de boleto
do Financeiro; migration 0004; FinanceiroPage, LeitorCodigoFinanceiro, API
financeiro e styles.css, implementados anteriormente.

## Limitações e Git

Leitor USB físico e todos os tamanhos de tela não foram testados nesta retomada.
Não foi repetida a suíte PostgreSQL de 12/09; o banco local foi consultado para
check e estado de migrations, e os testes atuais usaram settings de teste.
Sem commit, push ou merge. Não foram alterados ou excluídos dados existentes.
