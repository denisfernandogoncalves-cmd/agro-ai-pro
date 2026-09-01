# Contratos e correções de lançamentos comerciais — 30/08/2026

## Entrega

Cadastros agrícolas agora inclui Contratos com Empresa, Nº do contrato,
Quantidade (kg) e Produto. Vendas permite selecionar contrato/empresa e sugere
a quantidade cadastrada. As telas aceitam quantidades no padrão brasileiro.
O cadastro não movimenta estoque e não exige uma propriedade previamente criada.

Vendas, entregas e devoluções podem ser editadas ou excluídas com motivo,
confirmação de exclusão, controle de versão, idempotência e auditoria. Ações de
exclusão preservam a trilha e ajustam os saldos por estornos. Dependências,
saldo insuficiente ou capacidade insuficiente impedem a operação inteira.
Contratos excluídos deixam de aparecer em novas vendas e podem ser reativados.

As alterações anteriores de propriedades, rateios e números foram preservadas.
O pedido separado de limpeza foi executado com backup; detalhes em
`2026-08-30-limpeza-testes.md`. Após as validações, o banco operacional tem zero
registros em suas 40 tabelas de dados de negócio/cache e mantém dois usuários.

## Arquivos desta entrega

- Backend comercial: `apps/vendas/models.py`, `serializers.py`, `views.py`,
  `services.py`, `alteracoes_services.py`, `selectors.py`, `urls.py`, `admin.py`.
- `apps/vendas/migrations/0003_*`, `0004_*`, `0005_*`: contrato, auditoria,
  exclusão lógica, importação de contratos legados, produto e quantidade.
- `apps/graos/services.py`: proteção contra estorno genérico comercial e
  correspondência do lote com a propriedade da posição.
- `apps/relatorios/selectors.py`: excluir registros comerciais anulados.
- `apps/vendas/test_alteracoes.py`: 14 testes adicionais, incluindo concorrência.
- Frontend: `api/contratosComerciais.ts`, `api/vendas.ts`,
  `pages/CadastrosAgricolas/ContratosComerciais.tsx`,
  `pages/CadastrosAgricolas/CadastrosAgricolasPage.tsx`,
  `pages/Vendas/VendasPage.tsx`, `pages/Vendas/EditorLancamentoVenda.tsx`,
  `styles.css`, `scripts/test-components.mjs`.
- Documentação: `docs/api/VENDAS.md`, `docs/api/CADASTROS_AGRICOLAS.md` e os
  registros de decisão desta entrega e da limpeza.

## Verificações executadas

- `docker compose -p agro-ai-pro exec -T -w /app/backend backend python manage.py test --noinput`:
  307 testes, 302 aprovados e 5 ignorados, em 140,966 s. Os cinco ignorados são
  da antiga API operacional de grupos de colheita, já retirada. Os testes
  comerciais de concorrência foram executados em PostgreSQL real.
- `npm.cmd test --prefix frontend`: 34 cenários de componentes/submissão/PWA e
  13 cenários de autenticação aprovados. Inclui conversão de `35.000,500` e
  rejeição de formatos ambíguos, campos do contrato e bloqueio dos botões.
- `npm.cmd run build --prefix frontend`: TypeScript e Vite aprovados.
- `manage.py check`: sem problemas; `makemigrations --check --dry-run`: sem
  alterações pendentes; migrations comerciais 0003 a 0005 aplicadas no banco local.
- Build Docker do frontend aprovado e serviço atualizado na porta 5174.
- Navegador autenticado: Propriedades vazias, formulário Contratos com os quatro
  campos e lista vazia, seletor Contrato/empresa na Nova venda, saídas e vendas
  vazias. Nenhum formulário foi salvo no banco operacional durante a validação.
- Contagem final: zero dados operacionais; dois usuários preservados.
- `git -c core.safecrlf=false diff --check`: aprovado. Diff revisado; backup
  fora da área pública e ignorado pelo Git.

## Limites e decisões

A quantidade no cadastro é informativa/sugestão, sem novo teto agregado entre
vendas do mesmo contrato. A cultura efetiva continua definida pela posição de
estoque. O produto cadastrado não cria automaticamente estoque nem posições.
Alterações cadastrais não reescrevem os dados históricos das vendas.

A interface de edição com registros preenchidos não foi exercitada no banco
operacional, para respeitar o pedido de mantê-lo vazio. Os efeitos de edição e
exclusão foram validados pela API e serviços em banco separado. O build mantém
o aviso preexistente de bundle maior que 500 kB. Não há script de lint no projeto.

Branch `codex/remover-grupos-colheita`, com alterações locais anteriores
preservadas. Sem commit, push, merge ou publicação em produção. Sem pendência
impeditiva conhecida para esta entrega.
