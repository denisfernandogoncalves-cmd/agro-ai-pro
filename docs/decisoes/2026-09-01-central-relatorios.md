# Centralização de relatórios — 01/09/2026

## Solicitação

O Product Owner solicitou que todos os relatórios possíveis do sistema ficassem
disponíveis na aba **Relatórios**.

## Decisão

A aba foi transformada em uma central somente leitura. Os módulos operacionais
continuam responsáveis por cadastros e mutações; a central reutiliza seus
modelos e o endpoint autenticado de relatórios, sem copiar dados nem criar uma
segunda fonte de verdade.

Foram preservados os dez relatórios de grãos existentes e acrescentadas oito
famílias: estrutura rural, financeiro, estoque de insumos, operações agrícolas,
máquinas e custos, clima, mercado/Corn Belt e auditoria de importações.

Os filtros globais são aplicados apenas quando têm significado para o relatório.
Propriedade, proprietário, cultura, safra e período atravessam as famílias
compatíveis; filtros comerciais e do ledger permanecem restritos a grãos e
vendas. As telas originais não foram removidas.

## Segurança e dados

Antes da implementação foi criado e validado o backup privado
`backups/antes-relatorios-centralizados-2026-09-01-212551-920438`, contendo
código, alterações locais, arquivos não rastreados, banco PostgreSQL, uploads,
catálogo e hashes SHA-256. Nenhum dado foi convertido, restaurado ou excluído.
Não foi necessária migration.

## Critérios de aceite

- todos os grupos aparecem dentro da aba Relatórios;
- todas as consultas exigem autenticação e aceitam somente leitura;
- respostas são paginadas e preservam filtros aplicáveis;
- áreas são apresentadas em alqueire paulista;
- relatórios existentes de produção e impressão continuam funcionando;
- backend, frontend, build, migrations e navegação visual são validados antes
  da conclusão.
