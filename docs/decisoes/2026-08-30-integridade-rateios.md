# Integridade e concorrência de cargas rateadas — 30/08/2026

## Contexto e escopo

Continuação solicitada após a retomada de Produção e Saldos. Branch
`codex/remover-grupos-colheita`, no worktree `runtime-origin-main`.
O objetivo desta etapa é preservar o ciclo de vida da carga ao estornar suas
parcelas e permitir operações concorrentes sem inversão dos bloqueios.
Não houve alteração da fórmula de rateio, das regras de desconto ou do esquema.

## Falhas reproduzidas antes da correção

1. A proteção do estorno genérico identificava somente a movimentação principal
   por `carga_colhida`. Uma parcela secundária, vinculada por
   `rateio_carga_colhida`, podia ser estornada isoladamente. O teste da API
   retornou HTTP 201 quando deveria retornar conflito, deixando a carga ativa
   com uma parcela estornada.
2. Registro, cancelamento e correção adquiriam bloqueios à medida que percorriam
   as parcelas. Duas cargas com os CAD/PROs distribuídos de forma cruzada entre
   as propriedades podiam bloquear esses CAD/PROs em ordem inversa. Três testes
   com conexões PostgreSQL independentes reproduziram `DeadlockDetected`, um
   para cada operação.

## Decisão e implementação

O estorno genérico agora reconhece ambos os vínculos. A operação deve passar
pelo cancelamento ou pela correção da própria carga. O sinalizador interno que
permite esse estorno continua fora do contrato de entrada da API.

As operações de carga bloqueiam todos os CAD/PROs em ordem de UUID antes dos
armazéns e da primeira parcela. Na correção, o conjunto inclui os recursos das
parcelas antigas e das novas. Escolhas implícitas de CAD/PRO são resolvidas e
fixadas antes dos bloqueios, para a gravação subsequente não escolher outro
titular fora do conjunto já bloqueado.

A solução mantém transações e serviços existentes. Não foi adotada repetição
automática após deadlock: a causa da ordem inversa foi eliminada nos cenários
reproduzidos. Operações que compartilham CAD/PROs podem aguardar a transação
anterior, preservando a serialização necessária aos saldos.

## Arquivos desta etapa

- `backend/apps/graos/services.py`: proteção de estorno de parcelas secundárias;
- `backend/apps/graos/cargas_services.py`: bloqueio antecipado de todos os recursos;
- `backend/apps/graos/test_cargas_colhidas.py`: quatro novos testes de API e integridade;
- `backend/apps/graos/test_rateios_concorrencia.py`: três novos testes PostgreSQL;
- `docs/api/CARGAS_COLHIDAS.md` e `docs/api/GRAOS.md`: contratos e ordem de bloqueio;
- este relatório.

Os testes novos verificam rejeição pelas duas rotas de estorno, inclusive quando
o cliente tenta enviar o sinalizador interno, cancelamento idempotente de todas
as parcelas, substituição completa e rollback quando uma parcela tem reserva.
Os testes concorrentes intercalam parcelas por uma barreira com limite de tempo,
usam transações reais e conferem saldos, estados das cargas e movimentos finais.

## Validações direcionadas

Na raiz do worktree:

```powershell
docker compose -p agro-ai-pro exec -T -w /app/backend backend python manage.py test apps.graos.test_rateios_concorrencia apps.graos.test_cargas_colhidas apps.graos.test_cargas_concorrencia --noinput --keepdb
```

Resultado: 25 testes aprovados no PostgreSQL, incluindo os cenários antes
reproduzidos como falha. O banco de testes é separado do operacional e foi
preservado com `--keepdb`.

Na pasta `backend`, com `DJANGO_SETTINGS_MODULE=config.settings.test`:

```powershell
python manage.py test apps.graos.test_cargas_colhidas --noinput
```

Resultado: 21 testes aprovados no SQLite após as correções.

Na pasta `frontend`:

```powershell
npm.cmd test
npm.cmd run build
```

Resultado: 25 cenários de componentes/submissão/geometria/PWA e 13 cenários de
autenticação aprovados; TypeScript e build aprovados. Não existe script `lint`.
Permanece o aviso não bloqueante de bundle acima de 500 kB.

## Regressão completa e migrations

Na raiz do worktree:

```powershell
docker compose -p agro-ai-pro exec -T -w /app/backend backend python manage.py check
docker compose -p agro-ai-pro exec -T -w /app/backend backend python manage.py makemigrations --check --dry-run
docker compose -p agro-ai-pro exec -T -w /app/backend backend python manage.py migrate --check
docker compose -p agro-ai-pro exec -T -w /app/backend backend python manage.py test --noinput --keepdb
git -c core.safecrlf=false diff --check
```

Resultado: verificações aprovadas, sem migrations pendentes ou mudanças de
esquema detectadas; **275 testes encontrados, 270 aprovados e 5 ignorados
previstos**, em 105,668 segundos. Diff sem erros de espaço.

## Verificação operacional somente leitura

A consulta por relações de rateio retornou:

- cargas ativas com parcela estornada: **0**;
- cargas canceladas com parcela sem estorno: **0**.

Essas duas contagens não equivalem a uma auditoria completa dos dados históricos.
Não houve reconciliação nem gravação de cargas operacionais. Os quatro serviços
Docker permanecem saudáveis, com frontend na porta 5174.

## Git e limites

Nenhum model, migration ou dependência foi alterado nesta etapa. As migrations
0010–0012 preexistentes continuam junto da entrega anterior, sem commit.
Arquivos preexistentes, backups e demais worktrees foram preservados.
Commit, push e merge não foram realizados. A entrega para o repositório remoto
continua dependente das autorizações previstas em `AGENTS.md`.
