# Correção e cancelamento com histórico — 14/10/2026

O Product Owner aprovou correção/cancelamento com o original preservado. Foram
expostos controles de editar/excluir em caminhões, lançamentos, remunerações,
frota, manutenções planejadas, operações planejadas e lotes. Registros com vínculos
continuam protegidos; campos calculados e consultas externas permanecem derivados.

## Históricos encerrados

O componente CorrecaoHistorico exige motivo e captura a versão ao abrir a edição.
As ações PATCH corrigir e DELETE cancelar-registro validam permissões e versão,
executam efeitos em transação e guardam todos os campos originais e o motivo no
RegistroAlteracao imutável. Uma falha desfaz tanto os efeitos quanto a auditoria.

- Estoque: corrige movimentações e valida todo o saldo cronológico. Movimentos de
  compra/operação devem ser tratados pela origem, sem edição independente.
- Operações encerradas: corrige campos permitidos; cancelamento desfaz consumos e
  marca a operação cancelada. Insumos têm correção/cancelamento com ajuste do saldo.
- Uso, abastecimento e manutenção de máquinas: correção/cancelamento exige confirmação
  explícita do horímetro atual e da versão da máquina. Leituras mantidas e usos
  sobrepostos impedem correção inconsistente; manutenção cancelada não soma custo.
- Frete conferido: cancelamento retira sua comissão dos totais. Original preservado.
- Remuneração: correção permite salário, percentual e comissão manual histórica,
  sem duplicar as comissões de frete; remuneração vinculada não é excluída diretamente.

Cadastros com histórico protegido devem ser desativados ou ter seus vínculos
tratados antes da exclusão. Não há exclusão em massa nem alterações em dados reais
para testar esta entrega. Auditoria não equivale a cobertura de SQL/bulk externo.

## Verificações e limites

- Backups anteriores verificados: visual-20261014-142149, 142920 e 143349.
- Antes das mudanças simultâneas de produtos: 148 casos PostgreSQL, 147 aprovados,
  um skip; depois, 25 casos específicos de correção aprovados.
- Verificação final de máquina/frete/remuneração: 13 casos aprovados; inclui comissão
  manual 50→60 com frete adicional 100, total 160 e original 50 preservado.
- Última suíte completa de correção: 26 casos, seis erros pela ausência da migration
  dos campos agronômicos de produtos introduzidos simultaneamente em outra tarefa.
  Não criamos/aplicamos essa migration nem alteramos o banco operacional.
- npm test aprovado. Build encontrou edição de produto sem novos campos; formulário
  corrigido para carregar todos os valores. Reteste de build requerido.
- Sem migrations novas para o protocolo de correção. Conferência visual autenticada
  indisponível: navegador automatizado falhou ao inicializar seus assets.
- Propriedades, talhões, cargas, vendas, CAD/PRO, financeiro e transferências mantêm
  suas ações específicas existentes; não foi feita auditoria integral de cada campo.

Principais arquivos: core/correcoes.py e test_correcoes_historico.py; serializers/views
em estoque, producao, maquinas e transportes; frontend/components/CorrecaoHistorico.tsx;
APIs e páginas correspondentes. Alterações simultâneas preservadas. Implantação final
pendente da estabilização da base; não declarar conclusão global ou merge aprovado.