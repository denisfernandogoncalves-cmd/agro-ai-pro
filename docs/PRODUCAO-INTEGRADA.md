# Gestão Integrada da Produção Agrícola

## Objetivo

Substituir os controles legados de produção e comercialização por um domínio transacional integrado ao AGRO-AI-PRO, preservando a rastreabilidade por propriedade e as permissões multiusuário.

## Princípios

- o módulo `producao` continua responsável pelas operações agrícolas e passa a concentrar o domínio de grãos;
- `Propriedade`, `Talhao`, `ParceiroFinanceiro`, `LocalEstoque` e `LancamentoFinanceiro` são reutilizados;
- o estoque de grãos usa livro-razão próprio, porque possui dimensões obrigatórias de CAD/PRO, cultura, safra, talhão e qualidade que não existem no estoque de insumos;
- nenhuma movimentação confirmada é editada ou apagada; correções são feitas por estorno;
- confirmações de recebimentos, transferências e embarques são atômicas;
- o saldo nunca pode ficar negativo;
- o frontend não substitui as autorizações do backend;
- consultas são filtradas por propriedade e por CAD/PRO autorizado.

## Referências funcionais analisadas

As referências disponíveis incluem notas fiscais de grãos com produtor, comprador, motorista, placas, quantidade, preço, valor e destino, além de planilhas de compras e retiradas de insumos. Não foi encontrada uma planilha específica de recebimento e estoque de grãos; por isso, regras comerciais de desconto de qualidade não são presumidas. O peso líquido informado pela balança é validado, mas não recalculado por uma fórmula inventada.

## Reutilização dos módulos existentes

| Conceito | Origem |
| --- | --- |
| Propriedade | `apps.propriedades.Propriedade` |
| Talhão | `apps.talhoes.Talhao` |
| Comprador, terceiro e transportador | `apps.financeiro.ParceiroFinanceiro` |
| Silo e armazém | `apps.estoque.LocalEstoque` |
| Receita de venda | `apps.financeiro.LancamentoFinanceiro` |
| Papéis administrador, gestor, operador e leitura | `apps.core.access` e `AcessoPropriedade` |
| Mercado e tendências | `apps.mercado` |
| Insights explicáveis | `apps.ai` |

## Novos agregados

### CadPro

Cadastro obrigatório por propriedade, com código, titular, inscrição estadual e controle de acesso por usuário.

### SafraAgricola e CulturaAgricola

Catálogos usados pelo novo domínio. Os campos de texto legados dos demais módulos permanecem compatíveis e podem ser migrados posteriormente sem quebra de API.

### RecebimentoProducao

Carga recebida com motorista, veículo, romaneio, origem, qualidade, pesos, local e dimensões produtivas. A confirmação cria uma entrada imutável no livro-razão.

### MovimentoGraos

Livro-razão de entradas e saídas em quilogramas. Transferências geram dois lançamentos vinculados pelo mesmo grupo. Ajustes e estornos exigem justificativa e auditoria.

### ContratoProducao

Compromisso comercial por comprador, CAD/PRO, cultura, safra, quantidade, preço e período. O saldo entregue é derivado dos embarques confirmados.

### EmbarqueProducao

Saída comercial vinculada ao estoque disponível. A confirmação baixa o saldo, atualiza o contrato e cria uma conta a receber no Financeiro.

### NotaFiscalProducao

Documento fiscal do produtor ou da empresa, associado a recebimento ou embarque.

### AuditoriaProducao

Registro imutável de confirmações, cancelamentos, transferências, ajustes, estornos e importações.

### ImportacaoLegado

Assistente de CSV/XLSX com detecção de colunas, mapeamento manual, pré-visualização, validação e confirmação transacional.

## Unidades

A unidade canônica do livro-razão é quilograma. Toneladas e sacas são projeções. O peso da saca é configurado em `CulturaAgricola`, com 60 kg como valor inicial editável.

## Segurança

- superusuário: acesso completo;
- administrador da propriedade: todos os CAD/PRO da propriedade e administração de acessos;
- gestor, operador e leitura: somente CAD/PRO explicitamente autorizados;
- gestor: cadastros, contratos e ajustes;
- operador: recebimentos, transferências e embarques;
- leitura: consultas, dashboard e relatórios;
- IDs externos à propriedade ou ao CAD/PRO autorizado retornam HTTP 404;
- ações incompatíveis com o papel retornam HTTP 403.

## Fluxos transacionais

### Confirmar recebimento

1. validar propriedade, CAD/PRO, safra, cultura, talhão e local;
2. validar pesos e percentuais de qualidade;
3. bloquear o recebimento para atualização;
4. criar entrada no livro-razão;
5. marcar como confirmado;
6. registrar auditoria.

### Transferir estoque

1. bloquear os saldos de origem;
2. validar saldo disponível;
3. criar saída e entrada com o mesmo identificador de grupo;
4. registrar auditoria.

### Confirmar embarque

1. bloquear o estoque de origem e o contrato;
2. validar saldo físico e saldo contratual;
3. criar saída no livro-razão;
4. criar conta a receber no Financeiro;
5. marcar o embarque como confirmado;
6. registrar auditoria.

### Estornar

Estornos nunca apagam registros. Um movimento inverso é criado, associado ao registro original e acompanhado de justificativa e auditoria.

## Importação legada

Formatos aceitos: CSV e XLSX. O arquivo é analisado sem importar dados. A confirmação exige um mapeamento válido, dimensões autorizadas e ausência de erros bloqueantes. Cada linha importada conserva o número da linha e o arquivo de origem na auditoria.

## Relatórios

Filtros: propriedade, CAD/PRO, talhão, cultura, safra, comprador, contrato, motorista, placa, local e período. Formatos: JSON, CSV, XLSX e PDF.

## Evolução prevista

- regras configuráveis de descontos de qualidade por cultura e comprador;
- integração com balanças;
- importação de XML de NF-e/NFP-e;
- imagens de satélite e estimativas produtivas;
- conciliação fiscal e financeira avançada.
