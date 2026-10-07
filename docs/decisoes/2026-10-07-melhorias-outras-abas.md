# Melhorias autorizadas nas outras abas

## Entregas

- Painel: atalhos dos indicadores com relatório correspondente, respeitando
  permissão de consulta, propriedade e safra aplicadas. Abrem a seção de relatório
  correspondente; uma seção pode incluir mais tipos que o indicador isolado.
- Cargas próprias: descontos em kg separados em umidade, classificação e PH;
  prévia de líquido e rateio por propriedade/CAD/PRO existentes preservadas.
- Produção e saldos: composição completa das posições filtradas agrupada por
  operação, com efeitos assinados no físico/comprometido, estornos e recebimentos
  externos separados. Não depende da lista parcial do histórico.
- Transferências: origem/destino lado a lado identificados, preservando prévia
  antes/depois, versão, saldo disponível e motivos de bloqueio existentes.
- Vendas: restante a entregar desconta entregas e cancelamentos. Aviso de peso
  acima do restante antes da entrega. Não altera permissões de sobra técnica.
- Financeiro: vencido, próximo de vencer (sete dias) e diferenças entre título
  e liquidação destacados. O diálogo informa que liquidar encerra o título.
- Estoque: lotes ordenados pela validade, validade/saldo na seleção, próximos
  de vencer destacados. Sugestão de prioridade é manual entre produto/local
  compatíveis; vencidos não são selecionados ou movimentados automaticamente.
- Talhões: divergência entre área declarada e calculada destacada para revisão.
- Relatórios: critérios e unidades na tela/Excel e PDF com filtros, totais e
  registros. PDF até 1.000 registros; acima disso exige filtros menores ou Excel.
  Nenhuma linha é silenciosamente cortada. Excel preserva limite de 100.000.

## Critérios e limites

Somente estoque é transferido de terceiros; não soma produção, área, média ou
produtividade. Nenhuma migration, dependência ou reclassificação histórica.
Diferença de liquidação não vira saldo pendente: pagamentos parciais sucessivos
exigiriam regra de negócio e modelo próprios e não foram introduzidos.
PDF usa os campos técnicos completos em formato de conferência, não documento
fiscal. Campos _hectares estão em ha; tela usa alqueire paulista (2,42 ha).

## Evidências

Backup código/banco/uploads verificado e restaurado em isolamento:
`backups/agro-ai-pro-2026-10-07-151626-713302`.
30 testes PostgreSQL isolados de graos/relatorios aprovados, incluindo composição
conservada, origem externa, estorno, filtros, Excel, PDF, limite e permissões.
Frontend, componentes, autenticação, rascunhos, usabilidade, novos cenários de
restante/validades/diferenças, TypeScript e Vite aprovados no Docker.
Migrations sem alterações pendentes; git diff --check aprovado.
Durante validação foram corrigidos fechamentos JSX e tipo numérico da formatação;
resultados dos descontos originais permanecem os mesmos.
Sem commit, push, merge ou publicação em produção.

Aplicação local atualizada após segundo backup verificado
`backups/agro-ai-pro-2026-10-07-153431-867147`; frontend saudável.
QA autenticado confirmou o atalho Produção líquida abrindo Produção por
Propriedade/CAD-PRO, botão PDF e contexto/unidades. Composição de saldos
visível, sem alertas e sem transbordamento horizontal em 1265 px.
Nenhuma movimentação fictícia gravada durante a conferência.
