# Melhorias de interface autorizadas — 01/10/2026

## Escopo e critérios de aceite

Aplicar as cinco melhorias autorizadas após a auditoria: navegação agrupada por área com respeito aos acessos; textos secundários legíveis e datas brasileiras; cadastros recolhíveis separados de consultas; estados de carregamento/vazio e bloqueio de submissões simultâneas; busca de usuários e permissões por área.

Nenhuma mudança de regra de negócio, permissão real, credencial ou migration. Não remover campos nem funcionalidades. Preservar impressão e quebra responsiva; conferir teclado e larguras 360/768/1366 nos fluxos afetados.

Checkout: `.worktrees/runtime-origin-main`, branch `codex/propriedades-impressao-a4-20260921`. Alterações anteriores preservadas. Backup privado antes da edição: `backups/sincronizacao-20261001-140105`, 13 worktrees e uploads, bundle/ZIPs verificados, PostgreSQL `postgres.dump` validado com 620 linhas em `pg_restore --list` e SHA-256 no manifesto.

## Validação

Concluído em 02/10/2026 após a retomada solicitada pelo Product Owner. Backup adicional `backups/sincronizacao-20261002-071101`: 13 worktrees, código não commitado e uploads preservados; ZIPs/bundle verificados; dump PostgreSQL validado com 620 linhas em `pg_restore --list` e hash SHA-256 em `manifesto-dump.json`. Os serviços existentes foram reiniciados após a parada do Docker, sem restauração de dados.

## Alterações entregues

- `frontend/src/components/gruposModulos.ts` e `NavegacaoModulos.tsx`: seis áreas, submenus somente com os módulos já permitidos; Usuários continua exclusivo dos administradores.
- `PainelFormulario.tsx`: cadastros recolhidos inicialmente, campos preservados ao recolher, abertura e foco no primeiro campo ao selecionar uma edição; operação por teclado.
- `frontend/src/App.tsx` e páginas de Propriedades, Talhões, Cadastros agrícolas/Contratos, Cargas, Produção e saldos, Vendas, Compras/Estoque, Financeiro, Operações, Máquinas e Usuários: cadastros separados das consultas.
- `UsuariosPage.tsx`: busca por usuário, nome, sobrenome ou e-mail, sem distinguir acentos/maiúsculas; contagem dos resultados; permissões agrupadas e seleção individual, por área ou de todos os módulos.
- `utils/datas.ts` e páginas de Cargas, Vendas, Produção, Financeiro, Estoque, Operações, Máquinas, Mercado e Relatórios: datas de calendário DD/MM/AAAA na apresentação; os valores enviados às APIs e campos nativos de data continuam ISO.
- `RelatoriosPage.tsx` e `FinanceiroPage.tsx`: filtros avançados recolhíveis e resumo da consulta efetivamente aplicada; relatórios descartam respostas anteriores quando uma consulta mais recente já foi iniciada.
- App/login e cadastros de propriedades, usuários, máquinas, cargas, talhões/históricos, operações e financeiro: bloqueio síncrono de mutações concorrentes, botões desabilitados e avisos de processamento. As proteções e chaves de idempotência já existentes nos outros fluxos foram preservadas.
- `styles.css`: textos secundários das cargas e usuários em 14 px, menu responsivo com botões de pelo menos 44 px no celular, grades limitadas à largura disponível; tabelas extensas conservam sua própria rolagem. Formulários e resumos da consulta não são acrescentados à impressão.
- `frontend/scripts/test-components.mjs`: busca sem acentos, cobertura dos 17 módulos sem duplicação, acesso restrito e navegação de administradores, datas sem deslocamento de calendário, painéis e estados iniciais de carregamento.

## Comandos e evidências

Executados no checkout acima:

- `npm.cmd --prefix frontend test`: aprovado, incluindo componentes/submissão e 14 cenários comportamentais de autenticação.
- `npm.cmd --prefix frontend run build`: TypeScript e Vite aprovados; 180 módulos. Aviso já existente de bundle acima de 500 kB (aproximadamente 686 kB), sem erro de compilação.
- `docker compose -p agro-ai-pro exec -T -w /app/backend backend python manage.py check`: sem problemas.
- `docker compose -p agro-ai-pro exec -T -w /app/backend backend python manage.py makemigrations --check --dry-run`: nenhuma alteração detectada.
- `docker compose -p agro-ai-pro exec -T -w /app/backend backend python manage.py test apps.accounts.test_user_access apps.core --noinput`: 23 testes aprovados no banco de testes isolado.
- `docker compose -p agro-ai-pro build frontend`: imagem final compilada.
- Com `FRONTEND_PORT=5174`, `docker compose -p agro-ai-pro up -d --no-deps --wait --wait-timeout 60 frontend`: frontend atualizado e saudável.
- `git diff --check`: aprovado, somente avisos de conversão de finais de linha já existentes.

Conferência no navegador integrado com sessão autenticada: propriedades carregadas, seis áreas do menu, busca GISELE retornando 1 de 2 usuários, edição abrindo com foco no input, seleção Comercial alterando somente o formulário de 17 para 14 e novamente para 17 módulos, cancelada sem salvar. Filtro de propriedade do relatório só altera o resumo após Aplicar filtros, passando de seis para dois registros de PEDRO CARIOCA. Tecla Enter abre/recolhe o painel de máquinas.

Usuários em edição, Financeiro com cadastro aberto e Relatórios com filtros avançados foram verificados a 360/768/1366 px, sem rolagem horizontal da página. Nas tabelas largas a rolagem permanece no contêiner (relatório a 360 px: tabela 850 px em contêiner 312 px). Cargas abertas verificadas a 360/768 px e lista a 1366 px; Operações abertas a 360 px. Cadastros agrícolas conservam os cinco formulários recolhíveis, incluindo Contratos. As fontes secundárias verificadas têm 14 px.

Evidências privadas: `backups/sincronizacao-20261002-071101/melhorias-telas-cargas.jpg` e `melhorias-telas-cargas-responsiva.jpg`. A captura em largura ampla do navegador integrado apresenta resolução reduzida; a segunda captura registra o cartão legível na largura padrão. Os tamanhos e ausência de estouro também foram medidos no DOM.

## Limites e riscos

Nenhuma migration ou alteração de regra de negócio neste incremento. As verificações visuais não registraram vendas, lançamentos, credenciais nem mudanças reais de permissões. O bloqueio no frontend impede requisições simultâneas por cliques repetidos; não substitui a idempotência no backend nem elimina incerteza de rede após uma gravação. Nenhuma promessa de garantia adicional de gravação foi introduzida. A impressão foi preservada pelo CSS e pelos testes existentes; não foi emitida impressão física. Não há script de lint no package.json. O aviso de tamanho do bundle fica registrado para otimização futura. Sem commit, push ou merge; alterações anteriores preservadas.
