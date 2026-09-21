# Continuidade de cargas, saldos, sobra técnica e rede local

Branch: `codex/grupos-propriedades-colheita`, checkout `runtime-origin-main`.
Base `489f66a`, com alterações preexistentes preservadas. A pasta principal
permaneceu em `feature/importacoes-confirmacao-v1`. Sem commit, push ou merge.

## Escopo e aceite

- Retomar a versão mais recente de cargas e saldos sem misturar a pasta principal.
- Crédito de produção respeita propriedade, CAD/PRO, cultura, safra,
  classificação e armazenagem; lote fora da seleção não pode ser submetido.
- Preservar autorização explícita do Product Owner para venda com saldo negativo
  por sobra técnica. Não criar crédito fictício, ocultar déficit ou duplicar venda.
- Disponibilizar a versão local na porta 5174 e preparar uso na mesma rede.
- Criar backup verificado no destino escolhido `D:\AGRO IA\Backups`.

## Alterações

- `frontend/src/pages/ProducaoSaldos/ProducaoSaldosPage.tsx`: filtros completos
  no seletor de crédito e mensagem de validação correspondente.
- `frontend/src/pages/Vendas/VendasPage.tsx`: explicação da sobra técnica.
- `frontend/scripts/test-components.mjs`: regressões dos filtros e mensagem;
  testes anteriores de grupos/importações preservados.
- `backend/apps/vendas/test_saldo_negativo.py`: teste de 200 kg registrados,
  venda de 300 kg, painel com -100 kg e repetição idempotente sem entrada fictícia.
- `docs/api/GRAOS.md` e `docs/api/VENDAS.md`: regras documentadas.
- `scripts/start-rede-local.ps1`: início do ambiente com IPv4 privado explícito.
- `scripts/liberar-rede-local.ps1`: regra restrita de firewall, executada como
  administrador após confirmação do Windows.
- `scripts/backup_local.py`: rotina baseada no backup existente, com destino
  configurável, verificação integral e pastas únicas.
- `docs/manuais/REDE-LOCAL-E-BACKUP.md` e este registro: operação e evidências.

Nenhum model ou migration alterado. `graos.0013` já permite saldo negativo
nas vendas e o serviço já utiliza essa permissão. Nenhuma venda operacional
foi criada. Os testes usam bancos separados.

## Preservação

Backups anteriores às alterações e às atualizações do ambiente:

- `backups/retomada-2026-09-10-071337-980709`: código, uploads e banco físico
  parado; 5.043 entradas lidas, ZIPs verificados e hashes no manifesto.
- `backups/retomada-2026-09-10-071717-676084`: banco ativo em formato custom,
  código e uploads; leitura integral sem restauração.
- `backups/retomada-2026-09-10-124504-283927`: antes do ajuste de rede.
- `D:\AGRO IA\Backups\agro-ai-pro-2026-09-10-124619-984110`: destino do usuário,
  seis arquivos verificados e manifesto; nenhuma cópia anterior sobrescrita.

## Verificações

Comandos de backend no diretório `backend`:

- `python manage.py test --settings=config.settings.test --noinput`:
  367 testes, 331 aprovados e 36 ignorados; a falha simulada de importação é
  parte do teste de rollback e não é uma falha da suíte.
- `python manage.py check --settings=config.settings.test`: aprovado.
- `python manage.py makemigrations --check --dry-run --settings=config.settings.test`:
  nenhuma alteração detectada.
- `docker compose -p agro-ai-pro run --rm --no-deps -T
  -e POSTGRES_DB=continuacao_20260910_0720 -w /app/backend backend python manage.py
  test apps.graos apps.vendas apps.talhoes.tests.test_grupos_colheita --keepdb --noinput`:
  PostgreSQL, 165 testes, 160 aprovados e 5 ignorados; banco de teste preservado.
- No banco local: `migrate --check`, `check` e `makemigrations --check --dry-run`
  aprovados. Nenhuma migration pendente aplicada nesta entrega.
- Frontend: `npm.cmd test` aprovado (suíte de componentes/submissão e 13
  cenários de autenticação); `npm.cmd run build` e build Docker aprovados.
- `git -c core.safecrlf=false diff --check`: aprovado.

## Ambiente e limitações

Backend, frontend, PostgreSQL e Redis iniciados. Porta 5174 configurada.
Página pelo IP `192.168.1.176` retornou HTTP 200; API respondeu `status=ok`
nesse endereço e por `127.0.0.1`. Após recriar o backend, o Nginx manteve o IP
interno anterior e retornou 502; reiniciar o frontend corrigiu a comunicação,
passo também incluído no script de inicialização.

A criação inicial da regra de firewall recebeu acesso negado; a execução
elevada foi autorizada e criou a regra habilitada para a rede privada.
Falta teste em outro computador e sessão visual autenticada nesta retomada.
Permanece aviso de bundle acima de 500 kB; não existe script de lint.
Backups em D: ainda dependem do mesmo disco; não há cópia externa ou agenda
automática configurada. O endereço DHCP pode mudar. Não houve publicação
em produção, restauração, remoção de funcionalidades ou alteração de credenciais.
