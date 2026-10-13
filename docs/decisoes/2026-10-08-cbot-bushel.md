# Preços CBOT em US$/bushel — 08/10/2026

Implementados no dashboard e na aba Mercado: soja ZS=F, milho ZC=F e trigo Chicago SRW ZW=F. Fonte pública Yahoo Finance / CBOT, com atraso; não representa ajuste oficial, tempo real ou preço recebido pelo produtor. Sem dependências novas ou serviço pago.

Consulta manual pelo botão Atualizar CBOT. Abrir a página apenas lê os últimos registros locais. Endpoint GET /api/mercado/cbot/; POST /api/mercado/cbot/atualizar/ exige permissão de cadastrar no módulo mercado. Não há atualização agendada. Falhas preservam os valores anteriores. Os três retornos são validados antes de uma transação atômica; identidade produto/contrato/horário impede duplicação e valores anteriores permanecem imutáveis.

O provedor retorna USX (centavos de dólar/bushel); dividir por 100 produz US$/bushel, com decimais preservados. Validam-se símbolo, bolsa CBT, unidade, preço positivo finito e horário. Contrato e horário original são apresentados, com fonte e idade. O contrato contínuo pode mudar no vencimento. Quando o provedor trunca o ano, a interface identifica a ausência sem inferir o vencimento. Indicadores FRED/FMI continuam separados e identificados como mensais, sem conversão indevida de tonelada para bushel.

A tentativa de acesso ao boletim público CME recebeu HTTP 403; não houve contorno da restrição. A consulta pública Yahoo respondeu para os três produtos. Fonte: https://finance.yahoo.com/quote/ZS%3DF/ ; especificações: https://www.cmegroup.com/markets/agriculture/oilseeds/soybean/specs . Disponibilidade da consulta pública não possui garantia de serviço.

Validações: 51 testes de mercado e relatórios aprovados em PostgreSQL isolado; testes de componentes, autenticação, rascunhos e usabilidade, TypeScript e build frontend aprovados. Migration mercado 0002 aplicada (somente tabela nova), Django check sem erros e makemigrations --check sem mudanças. Frontend atualizado e saudável na porta 5174. Cotações reais carregadas: soja 12,8925, milho 4,9850, trigo 6,8650 US$/bushel, horários originais 08/10/2026 13:48 UTC. Estes valores são evidência pontual e não previsão.

Backup privado de código, banco e uploads verificado antes das alterações e novamente antes da atualização: backups/agro-ai-pro-2026-10-08-105642-117137; seis arquivos, hashes validados e restauração exclusivamente isolada aprovada em verificacao-restauracao-20261008-105651-368618.json. Backups anteriores preservados.

Limitação: a sessão de navegador expirou após a atualização e exibiu login. Conferência visual autenticada desktop/celular e clique do botão na aplicação continuam pendentes; não foram registrados como aprovados. Permissões e comportamento do botão têm cobertura automatizada. Não houve alteração de produção, estoque, financeiro, credenciais, commit, push ou publicação.
