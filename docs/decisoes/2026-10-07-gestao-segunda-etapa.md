# Segunda etapa de gestão — implementação e validação

Autorização: sete melhorias propostas, sem EXE. Checkout runtime-origin-main;
preservar alterações locais da primeira etapa. Backup verificado inicial:
`backups/agro-ai-pro-2026-10-07-162437-393640` (código, banco e uploads).

Critérios: documentos mostram cancelamento/estorno real; checklist por usuário e
safra persiste responsável, observações, data e versão com histórico; financeiro
permite consultar títulos e anexar comprovantes pelas permissões existentes;
extrato por propriedade/CAD-PRO apresenta saldo inicial, movimentos e saldo final;
comparação reutiliza produção/área oficiais, discrimina custo de operações e exclui
estoque externo; pendências abrem sua origem identificada; controles e resultados
adaptados ao celular. Sem pagamentos/ajustes automáticos ou reclassificação histórica.

Modelo aditivo para checklist; autorização por ação, concorrência por versão e
auditoria. Consultas de extrato paginadas no servidor. Validar PostgreSQL isolado,
frontend/TypeScript/build, migrations e aplicação local antes de atualizar Sprints.

## Entrega validada em 07/10/2026

- Central de documentos distingue documentos ativos, cancelados, substituídos e
  movimentações estornadas conforme os registros reais.
- Checklist salvo por usuário e safra, com responsável, data, observações,
  controle de versão e histórico das últimas 25 revisões. Alterações não salvas
  são protegidas na navegação. Não substitui o fechamento oficial do período.
- Conferência financeira consulta todos os títulos ou somente liquidações com
  diferença; comprovantes reutilizam os anexos privados e permissões existentes.
- Extrato por propriedade/CAD-PRO traz saldo inicial, movimentações paginadas
  no servidor, saldo acumulado e final, identificando transferências externas e
  seus estornos.
- Comparação de safras reutiliza os indicadores oficiais de produção própria,
  área e produtividade. Transferências de terceiros não aumentam esses valores.
- Pendências permitem abrir o registro exato de origem, sem alterar seus dados.
- Controles das novas consultas adaptados ao celular, com tabelas de rolagem
  horizontal contida e botões maiores.

Endpoints: `core/checklist-safra/`, `core/extrato-cadpro/`,
`core/comparacao-safras/` e `core/pendencias-conferencia/<id>/origem/`.
Checklist exige ações de relatórios; extrato exige consulta de saldos; consulta
da origem exige a permissão do módulo correspondente. Custos somente são
exibidos com permissão de consulta de operações.

Limites: custos correspondem aos valores realizados das operações agrícolas,
atribuídos pela safra e cultura atuais do talhão; não consolidam todo o financeiro.
Operações sem custo informado são discriminadas. Checklist é individual por
usuário e safra. Nenhum ajuste automático ou reclassificação histórica foi feito.

## Verificações e ambiente

138 testes PostgreSQL aprovados com `scripts/test_backend_isolado.py` nos módulos
`apps.core`, `apps.relatorios`, `apps.financeiro` e
`apps.graos.test_melhorias_agendadas`. Incluem concorrência/versionamento do
checklist, permissões, origem exata, paginação/saldo, estornos e invariância da
produção diante de transferências externas. Testes frontend, TypeScript/Vite,
build Docker, Django check e consistência de migrations aprovados.

Migration aditiva `core.0004_checklist_safra` aplicada; frontend local atualizado
e saudável na porta 5174. Backup adicional antes da atualização:
`backups/agro-ai-pro-2026-10-07-165029-903677`. Ambos os backups incluem código,
banco e uploads, com integridade verificada e restauração ensaiada em isolamento.

Conferência autenticada no navegador: checklist carregado, comparação de safras,
documentos ativos/cancelados e extrato com nove movimentos e saldo final de
47.040 kg na consulta realizada. Layout conferido a 360 pixels sem extravasamento
horizontal da página. A consulta financeira operacional estava vazia; vínculo
e permissões foram verificados pelos testes isolados. Não foram criados registros
fictícios, anexos ou checklists no banco operacional para testar gravação.

Alterações anteriores preservadas. Sem EXE, commit, push, merge ou publicação em
produção nesta etapa. Diff revisado antes da conclusão.
