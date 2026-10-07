# Correções da auditoria e conclusão das melhorias

Autorização do Product Owner: corrigir os problemas e implementar as melhorias.
Checkout: `.worktrees/runtime-origin-main`, branch
`codex/melhorias-gestao-transferencias-20261003`. Mudanças anteriores preservadas;
sem commit, push, merge ou publicação em produção.

## Resultado

- Cadastro de terceiros com código único, nomes não únicos, ativação e edição.
  Novos recebimentos exigem cadastro na interface. Resumos, extratos e filtros
  usam identidade explícita; recebimentos antigos ficam separados até vínculo
  manual justificado. Excel identifica cadastro ou recebimento legado.
- Fechamentos incluem cargas próprias e terceiros. Histórico de classificação
  de terceiros é reconstruído pelos snapshots disponíveis, sem reescrever o
  livro de movimentos. Alterações de cargas próprias e terceiros em período
  fechado exigem confirmação e criam pendência. Repetição idempotente é
  reconhecida antes dessa confirmação; verificações e gravações usam locks.
- Fila de conferência com detalhe, responsável, motivo, situação, versão e
  histórico. Pesagens, divergências físicas e alterações confirmadas alimentam
  a fila. Permissões respeitam o módulo de origem. Não há ajuste automático.
- Retiradas de terceiros oferecem comprovante PDF e Excel (.xlsx), duas vias,
  motorista, destino, saldos e assinaturas. PDFs extensos continuam em páginas
  adicionais, preservando todo o texto. PDFs curtos mantêm duas vias em uma A4.
- Aba de terceiros carrega 25 recebimentos por página e permite carregar mais;
  consultas antigas sem paginação mantêm o contrato de lista. Fechamentos
  carregam movimentos em lote, evitando consultas repetidas por registro.
- Formulários protegem alterações não salvas. Dependências frontend fixadas;
  source-map-js atualizado para 1.2.2, eliminando a vulnerabilidade encontrada.
- PostgreSQL e Redis vinculados a 127.0.0.1; volumes existentes preservados.
  CI inclui PostgreSQL e usa runner com banco exclusivo, que recusa reutilizar
  banco preexistente. Testes frontend também integram o build Docker.

## Uso

Na aba Terceiros, abrir Cadastro de terceiros por código e cadastrar a pessoa.
Para recebimentos antigos, editar o recebimento, selecionar o cadastro correto
e justificar. Conferir identidade antes de vincular nomes iguais.
Fechamentos e Pendências de conferência estão nas telas de produção. Para
comprovante de retirada, abrir o histórico do recebimento e selecionar a saída.
Os botões oferecem PDF real e Excel moderno .xlsx.

## Backups e validação

Backups privados antes de alterações e atualizações de ambiente:
`backups/agro-ai-pro-2026-10-07-105016-080387`,
`backups/agro-ai-pro-2026-10-07-110940-737881` e
`backups/agro-ai-pro-2026-10-07-111732-161486`.
Integridade SHA256/CRC, restauração PostgreSQL isolada e extração/conferência
dos uploads aprovadas. Nenhuma restauração sobre o banco operacional.

Validação ampla: 346 testes PostgreSQL, cinco skips, sem falhas. Após os ajustes
finais de permissões, filas e consultas, 44 testes diretamente relacionados
passaram em banco temporário exclusivo, incluindo concorrência real. Frontend
validado por testes de componentes, autenticação, rascunhos e usabilidade,
TypeScript e build Docker. PDF extenso sintético renderizado em duas A4 e
inspecionado: texto final e assinaturas completos. Interface conferida em
360 px e desktop sem transbordamento horizontal.

Auditoria do lockfile: zero vulnerabilidades. A atualização pelo npm local
encontrou EPERM no cache node_modules do Windows; o lockfile foi atualizado
e o build Docker validou instalação limpa. Não foram alteradas permissões nem
apagado o cache. Não são necessárias migrations adicionais nesta correção.

## Limites relevantes

Recebimentos legados precisam de vínculo manual; nomes não identificam pessoas.
Histórico antigo sem snapshots suficientes usa metadados disponíveis, sem
inventar classificação passada. Extrato informa sua classificação atual;
fechamentos usam a reconstrução histórica disponível. Confirmação preventiva
de período cobre cargas próprias e terceiros, não todos os módulos do ERP.
CI remoto ainda não executado, pois não houve push. Testes e QA não criaram
registros fictícios no banco operacional.

Continuação autorizada e agendada: `2026-10-07-melhorias-agendadas-cadpro.md`.
Amplia a confirmação de períodos para o ledger das APIs de vendas, ajustes,
transferências e estornos, acrescenta conciliação e revisão manual de vínculos,
e valida transferência externa sem produção no CAD/PRO destinatário.
