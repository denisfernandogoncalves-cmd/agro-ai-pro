# Cavaco e diesel — edição, exclusão e contas a pagar

Entrega operacional em `codex/modernizacao-visual-runtime`, em continuidade às
decisões de cavaco e diesel. As regras abaixo substituem os limites anteriores
de ausência de exclusão e de integração financeira nesses documentos.

## Regras confirmadas pelo Product Owner

- Permitir editar/excluir cargas de cavaco e excluir lançamentos de compra de
  diesel da tela indicada. Exclusão lógica, com confirmação, sem remover história.
- Diesel: vencimento = data da compra + prazo em dias corridos, avançando para
  o próximo dia útil se cair em sábado, domingo ou feriado nacional. Manter o
  próprio dia quando já for útil. Mostrar automaticamente no formulário.
- Considerar somente feriados nacionais: sem feriados locais ou pontos
  facultativos. Calendário de 2026 conferido na relação oficial do
  [Sirc](https://www.sirc.gov.br/feriados-e-indisponibilidades-sirc/), distinguindo
  feriados de pontos facultativos. Incluída Paixão de Cristo; 20/11 a partir de 2024.
- Remover média ponderada do diesel, inclusive da resposta do resumo. O preço
  de abastecimento continua sendo o da última compra válida até sua data.
- Criar uma conta a pagar pendente por compra de diesel. Para compras existentes
  com pagamento Não informado, o usuário confirmou criação pendente e baixa
  posterior no Financeiro. Sem prazo, informar o prazo antes de gerar o título;
  não inventar vencimento desconhecido.
- Criar contas pendentes para **todas** as cargas de cavaco, inclusive aquelas
  indicadas como pagas na planilha. Escolha explícita do usuário para conferir e
  baixar depois. Preservar a marcação original como histórico, separada do status
  financeiro. Vencimento inicial na data de cada carga, ajustável no formulário
  da carga. Não aplicar automaticamente a regra de dia útil do diesel ao cavaco.

## Implementação e proteção dos dados

- Campos aditivos de exclusão: `estoque.0010` e `maquinas.0003`.
- Vínculos únicos de conta: `maquinas.0004` e `estoque.0011`; a última também
  acrescenta vencimento opcional ao cavaco. Todas aplicadas após backups.
- Serializer e view de cavaco; `maquinas/diesel.py`; seletor de preço em
  `transportes/diesel.py`; API e telas de cavaco/diesel no frontend.
- Botões de editar/excluir respeitam permissões. Excluir exige confirmação e
  retira o registro da consulta e dos totais, preservando dados e auditoria.
  Diesel exige a versão original para excluir e recusa requisição obsoleta.
- Serviço compartilhado `financeiro/origens.py`, com wrappers
  `estoque/cavaco_financeiro.py` e `maquinas/diesel_financeiro.py`: origem e título
  bloqueados na mesma transação; vínculo OneToOne impede duplicar o título.
- Edição atualiza valores/vencimento do título pendente. Exclusão cancela o
  título pendente. Títulos liquidados não são recalculados nem cancelados pela
  exclusão da origem. Falhas revertem toda a operação, inclusive a exclusão.
- Campos de origem no título não são sobrescritos por edição direta no
  Financeiro; ajustar preço/vencimento na compra ou carga. Liquidação usa o fluxo
  financeiro existente, com data e valor reais informados pelo usuário.
- Não foram removidos registros operacionais nem feitas baixas automáticas.
  Compras/cargas de valor zero não geram obrigação de valor fictício.

## Dados integrados e evidências

- Diesel: compras 1 e 2 vinculadas aos títulos 5 e 6, total R$ 85.260,00:
  R$ 42.540,00 em 23/10/2026; R$ 42.720,00 em 21/10/2026. Ambos pendentes.
- Cavaco: 32 cargas ativas (31 importadas e uma manual), 32 títulos pendentes,
  total R$ 291.550,45. Mantidas as 30 indicações históricas de pago na origem.
- Prévia antes da aplicação e nova simulação depois: zero títulos novos na
  repetição de ambos os scripts. Scripts, relatórios e auditoria de cada vínculo
  em `backups/diesel-financeiro-20261015` e `backups/cavaco-financeiro-20261015`,
  privados e ignorados pelo Git. Não foi atribuída falsamente uma sessão humana.
- Conferência autenticada pela API: todas as 34 contas visíveis em Contas a
  pagar, valores corretos e status pendente; marcações de cavaco preservadas;
  média removida do resumo; 09/10/2026 + 1 dia retorna 13/10/2026.

Backups completos com integridade e restauração isolada aprovadas antes das
etapas: `agro-ai-pro-2026-10-15-204924-269771`, `205050-555230`,
`205231-105637`, `205317-749072`, `205618-106380`, `205851-574813`,
`210120-957900` e, imediatamente antes da criação dos títulos de cavaco,
`backups/agro-ai-pro-2026-10-15-223417-660329`. Os nomes abreviados seguem
o mesmo prefixo `backups/agro-ai-pro-2026-10-15-`.

## Verificações

- 52 testes PostgreSQL isolados aprovados: cavaco, diesel, calendário e
  financeiro. Comando: `docker compose exec -T backend python
  scripts/test_backend_isolado.py apps.estoque.test_cavaco
  apps.maquinas.test_diesel_financeiro apps.transportes.test_diesel
  apps.financeiro.tests`.
- `check` sem problemas; `makemigrations --check --dry-run` sem diferenças.
- Build final Docker executou toda a suíte frontend, TypeScript e Vite com
  aprovação. Módulos anteriores preservados; sem novas dependências.
- Navegador Edge invisível, com API simulada: edição, prévia do vencimento,
  ausência da média, cancelar e confirmar exclusão de cavaco e diesel aprovados.
  Nenhum dado operacional foi alterado por testes visuais.
- Imagem frontend final ativada na porta 5174. `/api/ready/` retornou
  `{"status": "ok"}`. Agendamento de retomada desativado após execução para
  impedir repetição.
- Sem commit, push, merge ou publicação em produção. Impressão física não
  repetida nesta entrega; modelo de duas vias preservado.
