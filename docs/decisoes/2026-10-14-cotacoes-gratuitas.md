# Cotações gratuitas de Chicago — 14/10/2026

Objetivo: recuperar soja, milho e trigo no quadro de mercado após falha do Investing,
com preço, unidade, contrato, fonte e horário verificáveis, sem assinatura.

## Fonte e implementação

Yahoo Finance respondeu no backend para ZS=F, ZC=F e ZW=F, bolsa CBT e moeda USX.
Reutilizada a validação existente em mercado/cbot.py e a conversão de US¢/bushel
para US$/bushel. Novo GET autenticado /api/mercado/referencias/ consulta os três
grãos em paralelo e mantém USD/BRL pelo Investing. Endpoints anteriores preservados.
Nenhuma migration ou gravação em registros operacionais; somente cache.

Cache por 60 segundos, trava compartilhada, espera de cinco minutos após falha,
último preço por até sete dias com horário original. Resposta antiga não substitui
preço mais recente. A interface informa atraso e contrato; vencimento truncado não
é completado por suposição, e mercado aberto/fechado não é inferido sem dado.

Arquivos: backend/apps/mercado/{referencias.py,test_referencias.py,views.py,urls.py};
frontend/src/api/mercado.ts; frontend/src/components/QuadroCBOT.tsx;
frontend/src/pages/Mercado/MercadoPage.tsx; docs/SPRINTS.md.

## Evidências e verificações

- Backups privados verificados de código/alterações anteriores, uploads e banco:
  backups/visual-20261014-110603 e backups/visual-20261014-114526; manifesto com hashes.
- manage.py test apps.mercado.test_referencias apps.mercado.test_investing
  apps.mercado.test_cbot --settings=config.settings.test --noinput: 22 casos OK,
  SQLite em memória; banco operacional preservado.
- Docker compose build frontend: npm test, TypeScript e Vite aprovados.
- Django check e makemigrations --check --dry-run: OK, sem mudanças.
- Consulta real: soja 12,7925; milho 4,7975; trigo 6,6650 US$/bushel, cotados
  em 14/10/2026 às 11:34 de São Paulo; USD/BRL 5,0382 às 11:43. São amostras
  de validação, não valores fixados no código nem indicação de preço atual.
- Revisão do diff sem erros. Alterações anteriores de outras tarefas preservadas.
- Frontend atualizado na porta 5174, HTTP 200; endpoint autenticado retornou 200
  com os quatro preços e sem erros. Backend/frontend/PostgreSQL/Redis saudáveis.

## Limites e fontes pesquisadas

Yahoo exibe futuros CBOT com atraso: https://finance.yahoo.com/quote/ZS%3DF/.
Não é feed oficial da CME nem preço de ajuste; endpoint público pode sofrer
bloqueios ou mudanças. O trigo retornou nome truncado, identificado na interface.
Stooq retornou HTTP 404 no teste. Página CME expirou sem resposta; API oficial
documenta OAuth e acesso autorizado, portanto não foi contratada nem configurada.
API Barchart exige integração própria, sem evidência de acesso gratuito imediato.
Falhas locais de testes SSR no Windows e permissão do dist foram contornadas
pela validação existente no Docker, sem mudar dependências ou apagar artefatos.
Conferência visual autenticada não executada. Sem commit, push, merge ou produção.
