# Romaneios sem cerquilha — 09/10/2026

O usuário confirmou uso de http://127.0.0.1:5174/. A correção anterior havia
sido feita somente na montagem do EXE. Aplicado agora na branch
codex/modernizacao-visual-runtime: números sem # nas listas, títulos, campo
Romaneio, impressão e PDF/Excel de entrada própria, terceiros e saída.
IDs, cálculos, dados e sequências preservados.

Alterados: frontend/src/pages/CargasColhidas/{CargasColhidasPage.tsx,
romaneioTerceiro.ts,ListaRomaneiosEntrada.tsx,ExtratoTerceiro.tsx},
frontend/src/pages/Vendas/{RomaneioVenda.tsx,LocalizadorRomaneios.tsx},
backend/apps/graos/{romaneios_cargas.py,romaneios_terceiros.py} e
backend/apps/vendas/romaneios.py. Montagem Windows aceita fonte já corrigida.

Backup completo verificado: backups/visual-20261009-094922, na raiz principal,
código inclusive alterações locais, uploads, dump PostgreSQL, ZIP/CRC, catálogo
e hashes. Arquivos com gravação direta bloqueada pelas permissões existentes
foram editados por substituição atômica após autorização de execução.

npm test e npm run build no Dockerfile aprovados; seis testes de
apps.graos.test_romaneios_cargas e apps.vendas.test_alteracoes.DownloadRomaneioTests
aprovados pelo runner PostgreSQL exclusivo; Django check e git diff --check
aprovados. Primeira execução apontou módulo de testes inexistente, corrigido.

Frontend reconstruído: FRONTEND_PORT=5174,
docker compose -p agro-ai-pro up -d --build --no-deps frontend.
HTTP 200 em 5174 confirmou index-DISfMRlQ.js; serviços saudáveis.
Sem sessão disponível para conferir o navegador autenticado do usuário;
recarregar a aba carrega a interface nova. Sem migrations, instalação do EXE,
commit, push ou merge. Nenhuma alteração de dados operacionais.
