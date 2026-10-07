# Melhorias agendadas e transferência externa para CAD/PRO

Solicitação: executar uma vez em 07/10/2026 às 13h25, America/Sao_Paulo.
Automação: `melhorias-agro-ia-e-transfer-ncia-entre-cad-pro`.
Checkout confirmado pelo mount Docker: `.worktrees/runtime-origin-main`.
Branch: `codex/melhorias-gestao-transferencias-20261003`; alterações anteriores
preservadas. Sem commit, push, merge ou publicação em produção.

## Critérios de aceite e decisões

1. Vínculo manual por código, com versão, motivo, usuário e histórico;
   preservar peso e saldo, não unir pessoas automaticamente por nome.
2. Conciliação por armazém/produto/safra: comparar saldos com os livros de
   movimentos, discriminar operações próprias e de terceiros e exibir a
   diferença da última contagem contra o saldo registrado naquela ocasião.
   Consulta não altera estoque e usa lock comum do armazém para leitura estável.
3. Reutilizar contexto de auditoria da requisição e validação de fechamento
   no ponto central de gravação do ledger. Vendas, reservas, devoluções,
   ajustes, transferências e estornos pela API exigem confirmação em período
   fechado. Replays permanecem idempotentes; falhas revertem a operação inteira.
4. Histórico de terceiros mostra campos originais e corrigidos. Novos
   movimentos preservam snapshot completo do recebimento; registros antigos
   não são reescritos nem completados com dados históricos inventados.
5. Fila permite filtrar duplicidades e justificar recebimentos legítimos;
   decisão fica no histórico, sem exclusão automática.
6. Busca no servidor e páginas de 25 para recebimentos, vínculos,
   fechamentos e pendências. Contratos anteriores sem paginação preservados.
7. Painel de pendências com totais por situação, responsável, prioridade,
   idade e atrasos. Prazo opcional informado na conferência; sem prazo, não
   presumir atraso. Prioridade e prazo auditados junto à versão.
8. Transferência existente aceita outro CAD/PRO ativo e vinculado à propriedade
   destinatária, no mesmo armazém. Crédito é ajuste de titularidade de origem
   externa, nunca carga colhida: não acrescenta produção, área ou produtividade.
   A interface exige motivo. Ledger e movimento de terceiro mantêm usuário,
   destino, documento, quantidade e chave. Débito/crédito atômicos, validação
   de saldo disponível, permissões e estorno existentes preservados.

Foi encontrado e corrigido um defeito relacionado: `saldo_armazem` ignorava
terceiros quando ainda não existia posição própria no silo. O cálculo passou
a incluir esse estoque também no caminho legado; a transferência conserva
a ocupação física antes e depois, mesmo em armazém apenas de terceiros.

## Arquivos e endpoints

Backend: `graos/conferencia_operacional.py`, `terceiros.py`, `services.py`,
`pendencias.py`, `fechamentos.py`, `urls.py`, configuração CORS e testes.
Frontend: `ConferenciaOperacional.tsx`, `GestaoConferencia.tsx`, páginas de
terceiros, produção/saldos, vendas, transferências e conferência de posição;
API de terceiros e testes de componentes.

- `POST /api/graos/terceiros/entradas/{id}/vincular/`: cadastro, versão,
  motivo e Idempotency-Key; exige editar Cargas. Recebimentos estornados
  continuam somente no histórico, sem vínculo por esse fluxo.
- `GET /api/graos/conciliacao-estoque/`: armazem, cultura, safra; exige
  consultar Produção e saldos. Retorna diferenças e últimas evidências físicas.
- Recebimentos: `pagina`, `busca`, `sem_vinculo=true`.
- Fechamentos: `pagina`, `busca`; pendências: `pagina`, `busca`, `tipo`,
  `situacao`. PATCH de pendência aceita prioridade e data_limite opcionais,
  armazenadas nos detalhes existentes sem nova migration.
- CORS permite o cabeçalho `Confirmar-Periodo-Fechado`, indispensável à
  confirmação no frontend quando API e interface usam portas distintas.

## Backups e validação

Backups de código, banco e uploads antes das alterações e aplicação local:
`backups/agro-ai-pro-2026-10-07-140024-246734` e
`backups/agro-ai-pro-2026-10-07-141532-739881`. Integridade, hashes, CRC e
restauração conjunta em isolamento aprovados. Nenhuma restauração operacional.
Backup final antes da última aplicação:
`backups/agro-ai-pro-2026-10-07-142104-422276`, igualmente restaurado e verificado
em isolamento.
Código final e documentação preservados antes da aplicação definitiva em
`backups/agro-ai-pro-2026-10-07-142401-110590`; verificação e restauração
isolada também aprovadas.

Testes executados em bancos PostgreSQL temporários exclusivos, pelo script
`scripts/test_backend_isolado.py`. Validação frontend por npm test, TypeScript
e Vite via build Docker. Aplicação local atualizada após backup verificado.
339 testes backend executados, 334 aprovados e cinco skips, sem falhas, nos
módulos graos/vendas/relatorios/core, incluindo concorrência PostgreSQL.
23 testes finais de melhorias/auditoria aprovados após snapshots e permissões;
oito testes das melhorias revalidados após o agrupamento final da conciliação.
Django check sem erros; makemigrations --check --dry-run sem alterações.
git diff --check aprovado. Corrigidos durante validação um cadastro de teste
sem descrição obrigatória e uso de replaceAll incompatível com o alvo TypeScript.
Conferência autenticada das telas de vínculos, pendências e conciliação:
Soja 2026/2027, AGRO SILVESTRE, saldo próprio 47.040 kg e terceiros 47.160 kg,
diferenças de ambos os livros zero. Consulta somente de leitura.
Responsividade em 360 px: conteúdo e tela com 345 px úteis, sem alertas de erro
ou transbordamento. QA não registrou transferências, vínculos, vendas ou
conferências fictícias no banco operacional.

## Limites de uso

### Opção explícita para outra propriedade — 07/10/2026

O botão em Produção → Cargas colhidas → Terceiros passa a mostrar
“Transferir para outra propriedade”, com seleção da destinatária e de seu
CAD/PRO ativo. O histórico identifica a propriedade destinatária. A ajuda
explica que o recebimento altera somente o estoque, sem contabilizar produção,
área, média ou produtividade. O armazém físico permanece o mesmo.
Teste PostgreSQL isolado aprovado transferindo 30 kg de terceiros para uma
propriedade distinta: origem com 70 kg, destinatária com 30 kg, ocupação total
preservada e relatórios/indicadores de produção sem alteração. Testes frontend,
TypeScript e build Vite aprovados. Backup verificado antes das alterações.

Conciliação compara saldos de agora com movimentos completos; contagem física
é uma evidência datada, não uma medição atual. Divergências não são corrigidas
automaticamente. A classificação histórica usa os snapshots disponíveis.
Vínculo manual requer conferência documental e cadastro prévio.
Transferência preserva o armazém; mudança de armazenagem é outro movimento.
APIs antigas mantêm compatibilidade, incluindo observações opcionais em
transferências legadas; a interface atual exige motivo ao transferir.
