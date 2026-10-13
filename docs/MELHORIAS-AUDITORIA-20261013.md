# Melhorias da auditoria geral — 13/10/2026

## Escopo e critérios

Melhorias técnicas autorizadas sem contratação de serviços pagos. Preservar dados,
funcionalidades, acessos completos por padrão e a regra atual de mínimo por lote.
Os CAD/PRO faltantes serão cadastrados manualmente pelo Product Owner.
Critérios: testes pertinentes aprovados, migrations consistentes, instalação limpa,
serviços locais saudáveis, backups verificados e código operacional sincronizado
em sua branch própria, sem merge nem publicação em produção.

## Entregas implementadas

1. Limites de login por origem e conta, com limites próprios de renovação.
2. Limite adicional de autenticação no Nginx, com resposta 429.
3. Cache Redis compartilhado para limites entre processos; indisponibilidade
   retorna 503 e impede autenticação sem o controle de tentativas.
4. Perfil opcional de produção com Gunicorn, DEBUG desativado, chave/domínios/cache
   obrigatórios e cookies seguros. Não foi ativado no ambiente HTTP local.
5. Portas de PostgreSQL, Redis e backend restritas a 127.0.0.1. A interface mantém
   a porta 5174 para uso local/rede.
6. Histórico de alterações estendido a transportes/importações e contexto explícito
   de ator/origem para scripts; payloads livres e credenciais não são copiados.
7. Dependências frontend reinstaladas pelo lockfile; build TypeScript sem arquivo
   incremental protegido. Dependências antigas preservadas nos backups privados.
8. Indicador de estoque e insight identificam lotes abaixo do mínimo; cálculo atual
   preservado até a definição da regra de negócio.
9. Relatório de grãos só serializa a seção solicitada; ramos duplicados removidos.
10. Paginação REST opcional em propriedades, financeiro, estoque, máquinas e
    operações: page/page_size, padrão 50, máximo 200; sem parâmetros retorna lista.
11. Edição de financeiro, máquinas e operações exige atualizado_em_original;
    versão obsoleta retorna 409, sem sobrescrever o registro. Cliente financeiro
    envia a versão. Ações específicas conservam seus controles existentes.
12. Filtros de datas/IDs/intervalos recebem validação central e erro 400 consistente.
13. Cabeçalhos nosniff e Referrer-Policy; CSP em modo Report-Only para diagnóstico.
14. /api/ready/ consulta banco e cache, sem dados internos, com resposta 503 nas
    falhas; /api/health/ permanece verificação do processo.
15. Testes de coordenadas/romaneios incluídos em npm test; descoberta backend vazia
    falha no runner PostgreSQL; CI usa PostgreSQL, com rótulo apps explícito, check e migrations.
16. Constraints de quantidade positiva, valores não negativos e comissão de 0 a
    100 em transportes. Preflight não encontrou registros incompatíveis; migration
    transportes.0004 aplicada após backup. Nenhum registro foi ajustado.

## Arquivos principais

backend/apps/accounts/{views,throttles}.py; backend/apps/core/{auditoria,
edicao_concorrente,health,pagination,query_params,test_melhorias_auditoria}.py;
views de propriedades/financeiro/estoque/maquinas/producao/clima;
backend/apps/transportes/models.py e migrations/0004; relatorios/selectors.py;
backend/config/{urls.py,settings}; backend/requirements/base.txt;
docker-compose.yml; docker-compose.production.yml; docker/nginx/default.conf;
frontend/package.json; frontend/src/api/financeiro.ts; EstoquePage.tsx;
scripts/test_backend_isolado.py; .github/workflows/ci.yml.

## Evidências obtidas antes da pausa

- python scripts/test_backend_isolado.py apps: 762 casos, OK, seis skips,
  PostgreSQL exclusivo (430,948 s), sem testes no banco operacional.
- Após os ajustes finais de cache/auditoria/paginação: 103 casos pertinentes,
  OK, um skip (18,276 s). Não são 103 casos adicionais à suíte geral.
- Instalação npm ci: 73 pacotes instalados; auditoria incorporada reportou zero
  vulnerabilidades naquele momento. Não equivale a pentest.
- docker compose build frontend: npm test, TypeScript e Vite aprovados.
- Django check aprovado; makemigrations --check --dry-run sem mudanças;
  showmigrations confirmou transportes.0004 aplicada.
- Frontend/backend/PostgreSQL/Redis saudáveis; /api/ready/ pelo frontend: status ok.
- Perfil production verificado com chave temporária, sem alterar secrets:
  somente security.W005 e W021, pois subdomínios/preload HSTS não são presumidos.
- Nesta retomada: formatação CRCRLF de três arquivos corrigida e ajuste do rótulo
  de testes CI confirmado. Django check e migrations novamente aprovados.
- Verificação adicional SQLite: 763 casos, 47 skips e quatro erros de busca JSON
  PostgreSQL-específica. Não é o banco operacional; CI foi corrigido para testar
  integralmente no PostgreSQL oficial, mantendo check e migrations nesse banco.
  Não foram alteradas regras de busca para acomodar um banco não suportado.
- Reteste final no PostgreSQL oficial: 13 casos de core/melhorias e consulta de
  romaneios, OK, sem skips (6,096 s).
- docker compose -f docker-compose.yml -f docker-compose.production.yml config
  --quiet: aprovado com chave temporária, sem ativar o perfil.
- Revisão de diff e lista de envio: nenhum backup, .env, upload ou node_modules;
  busca de padrões de chave privada/token não encontrou ocorrência.

## Preservação e sincronização

Backup anterior às melhorias: principal backups/visual-20261012-225139-777786;
operacional backups/agro-ai-pro-2026-10-12-225142-982727.
Antes da migration/atualização: operacional
backups/agro-ai-pro-2026-10-13-042918-485875 (ZIP, dump e hashes verificados).
Retomada: principal backups/visual-20261013-191448-673439;
operacional backups/agro-ai-pro-2026-10-13-185955-938502: código, uploads e cópia
física do PostgreSQL parado, leitura integral e SHA-256 verificados. As tentativas
incompletas de backup também foram preservadas; não são backups válidos.

A versão operacional é a branch codex/modernizacao-visual-runtime, montada pelo
Docker a partir de .worktrees/runtime-origin-main. O checkpoint principal
codex/modernizacao-visual foi preservado. A consolidação consiste em registrar
integralmente a versão operacional em sua branch revisável, incluindo alterações
preexistentes testadas; não copiar migrations conflitantes nem fazer merge.
Instalações novas devem usar a branch operacional. Banco, uploads, .env, backups e
node_modules não devem ser enviados ao GitHub.

## Limites e pendências

- HTTPS exige terminação TLS e proxy confiável antes de ativar o perfil production.
  O ambiente local continua development; ele não é produção endurecida.
- CSP Report-Only não bloqueia scripts; tokens ainda permanecem no localStorage.
- Throttling DRF não é limite matematicamente estrito em concorrência; Nginx
  complementa a proteção por origem. Não substitui proteção contra DDoS.
- Auditoria por signals não cobre bulk_update/bulk_create/SQL direto automaticamente;
  scripts devem abrir contexto explícito. Não declarar rastreabilidade universal.
- Relatório de grãos ainda materializa coleções para totais; financeiro/máquinas/
  operações/insumos já paginavam no banco antes desta tarefa. Retificação do item
  10 da auditoria inicial: financeiro não tinha a falha ali atribuída.
- Paginação é opcional para preservar consumidores atuais. Não limita todas as
  consultas antigas nem foi realizado teste de carga.
- Transportes ainda não possui controle de versão em todas as edições.
- Idade/falhas de clima/mercado já possuem recursos anteriores; processamento em
  segundo plano, radar e outras propostas funcionais ficam para incrementos próprios.
- A árvore principal antiga permanece divergente, com limitações de build/migrations;
  não utilizá-la para recriar a versão operacional. Integração em main não realizada.
- Conferência manual integral de todas as telas, impressão física e pentest não feitos.
- Regra futura de mínimo, CAD/PRO faltantes e HTTPS dependem de informações futuras.
