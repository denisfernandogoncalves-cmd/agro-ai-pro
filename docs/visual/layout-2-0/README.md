# Evidências visuais — layout 2.0

Capturas de uma **demonstração isolada com dados fictícios e APIs interceptadas**.
Não mostram o banco operacional e não representam preço/clima reais. Os cenários
com registros antigos, vazios, falha e acesso restrito estão identificados.

| Tela | Antes | Depois desktop | Depois celular |
| --- | --- | --- | --- |
| Painel | [1440](antes-painel-1440.png) | [1440](depois-painel-1440.png) | [390](depois-painel-390.png) |
| Propriedades | [1440](antes-propriedades-1440.png) | [1440](depois-propriedades-1440.png) | [390](depois-propriedades-390.png) |
| Talhões | [1440](antes-talhoes-1440.png) | [1440](depois-talhoes-1440.png) | [390](depois-talhoes-390.png) |
| Produção e saldos | [1440](antes-producao-e-saldos-1440.png) | [1440](depois-producao-e-saldos-1440.png) | [390](depois-producao-e-saldos-390.png) |
| Vendas | [1440](antes-vendas-1440.png) | [1440](depois-vendas-1440.png) | [390](depois-vendas-390.png) |
| Mercado | [1440](antes-mercado-1440.png) | [1440](depois-mercado-1440.png) | [390](depois-mercado-390.png) |
| Clima | [1440](antes-clima-1440.png) | [1440](depois-clima-1440.png) | [390](depois-clima-390.png) |
| Máquinas | [1440](antes-maquinas-1440.png) | [1440](depois-maquinas-1440.png) | [390](depois-maquinas-390.png) |
| Transportes | [1440](antes-transportes-1440.png) | [1440](depois-transportes-1440.png) | [390](depois-transportes-390.png) |
| Assistente | [1440](antes-assistente-1440.png) | [1440](depois-assistente-1440.png) | [390](depois-assistente-390.png) |

Painel também em [1366](depois-painel-1366.png) e [768](depois-painel-768.png).
[Vazio](depois-painel-empty.png), [falha](depois-painel-error.png),
[acesso restrito](depois-permissao-mercado.png), [checks](checks.json).
PDFs demonstrativos: [saldos A4](impressao-saldos.pdf), [vendas A4](impressao-vendas.pdf).

## Reproduzir

Instalar as dependências pelo lockfile e executar `npm test` / `npm run build`
em frontend. Usar Node e Playwright do ambiente de ferramentas, sem adicionar
Playwright às dependências do produto. Na raiz da branch de revisão, definir
`AGRO_PLAYWRIGHT_MODULE` como caminho ao index.mjs do Playwright ou pacote resolvível.
Executar `node scripts/revisao_visual_layout.mjs`. Edge headless é o padrão;
`AGRO_BROWSER_CHANNEL` permite escolher outro canal instalado. Portas 5175/5176
precisam estar livres. `AGRO_VISUAL_BASE` permite selecionar outro commit de base.

O script lê apenas código Git da base, cria frontend temporário e intercepta todas
as APIs. Endpoints fora das fixtures retornam 503 explícito. Não requer usuário,
senha, .env, banco, upload ou acesso operacional. Nenhuma fixture entra no bundle.

## Checklist para o revisor

- [x] Testes frontend e build aprovados.
- [x] Capturas comparativas com dados fictícios identificados.
- [x] Layout desktop/tablet/celular e tabelas internas conferidos.
- [x] Busca por teclado, saída da sessão e navegação restrita na prévia.
- [x] Valores negativos/inconsistentes não viram composição de saldo positiva.
- [x] Componentes novos de saldo/fluxo ocultos na impressão A4.
- [ ] Estabilizar a migration de produtos já pendente na base preservada.
- [ ] Conferir salvamento, vendas, saldos, transferências e CAD-PRO com API isolada completa.
- [ ] Conferir KML/mapa/satélite e foto com origem externa disponível.
- [ ] Aprovação do Product Owner antes de qualquer merge ou implantação.
