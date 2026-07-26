# Gestão Integrada da Produção Agrícola

## Objetivo

O módulo substitui controles operacionais de produção mantidos em planilhas e integra recebimento, classificação de qualidade, estoque físico de grãos, contratos, embarques, Financeiro, auditoria, relatórios e insights explicáveis.

O domínio de **Operações agrícolas** existente continua responsável por preparo, plantio, pulverização, adubação, irrigação e colheita. O novo subdomínio de **Gestão da Produção** começa no recebimento físico da carga e não remove nem renomeia APIs anteriores.

## Reutilização de módulos

- `Propriedade` e `AcessoPropriedade`: identidade territorial e papéis da PR #16.
- `Talhao`: origem produtiva e cálculo de produtividade.
- `LocalEstoque`: silos, armazéns e demais locais físicos.
- `ParceiroFinanceiro`: compradores, transportadores e terceiros.
- `LancamentoFinanceiro`: contas a receber geradas por embarques confirmados.
- `OperacaoAgricola`: planejamento e execução das atividades de campo.
- Relatórios, Dashboard e Assistente: consolidação dos novos indicadores.

Não existe duplicação de propriedade, talhão, local de armazenagem, parceiro ou lançamento financeiro.

## Modelo de dados

### Cadastros

- `Cultura`: nome, código e peso padrão da saca em quilogramas.
- `Safra`: identificação e período opcional.
- `CadPro`: múltiplos CAD/PRO por propriedade.
- `AcessoCadPro`: escopo adicional por usuário dentro de uma propriedade.
- `Motorista` e `Veiculo`: logística e vínculo opcional com terceiros.
- `ContratoProducao`: comprador, quantidade, preço, prazo e tolerância.

### Operação física

- `RecebimentoProducao`: carga, balança, qualidade, origem e armazenagem.
- `SaldoGraos`: posição materializada por propriedade, CAD/PRO, talhão, cultura, safra e local.
- `MovimentacaoGraos`: entradas, saídas, transferências, ajustes e estornos.
- `EmbarqueProducao`: comercialização, documentos, transporte, quantidade e preço.

### Rastreabilidade

- `AuditoriaProducao`: usuário, ação, entidade, estado anterior, estado novo e metadados.
- `ImportacaoPlanilha`: arquivo, hash SHA-256, mapeamento, prévia, inconsistências e confirmação.

## Invariantes

1. Produção e comercialização exigem propriedade, CAD/PRO, cultura e safra.
2. O CAD/PRO deve pertencer à propriedade informada.
3. Talhão e local de armazenagem devem ser compatíveis com a propriedade.
4. O saldo de grãos nunca pode ser negativo.
5. Movimentações confirmadas não são editadas nem excluídas; correções usam estorno.
6. Recebimentos e embarques são criados como rascunho.
7. A confirmação de recebimento credita o estoque em transação única.
8. A confirmação de embarque valida estoque e contrato, baixa o estoque, cria a receita e registra auditoria na mesma transação.
9. Falhas em qualquer etapa revertem toda a operação.
10. Dados de outro escopo são filtrados antes da busca do objeto.

## Qualidade

O módulo registra umidade, impureza e defeitos entre 0% e 100%. Não existe desconto automático de peso porque nenhuma tabela ou fórmula comercial oficial foi definida. O peso líquido informado é validado contra peso bruto e tara. Regras de desconto poderão ser configuradas futuramente por contrato ou tabela de classificação, com versionamento e auditoria.

## Permissões

A autorização é composta por duas camadas:

1. papel na propriedade: administrador, gestor, operador ou somente leitura;
2. vínculo ativo ao CAD/PRO.

Superusuários mantêm acesso completo.

- Administrador: acessos, cadastros, ajustes, estornos e operação.
- Gestor: cadastros gerenciais, contratos, importação, ajustes, estornos e operação.
- Operador: recebimentos, embarques, transferências e confirmações operacionais.
- Somente leitura: consultas, dashboards, relatórios e insights.

A interface oculta ações incompatíveis, mas o backend permanece como proteção principal. IDs de outro escopo retornam HTTP 404; ações incompatíveis em recurso autorizado retornam HTTP 403.

## Fluxos

### Recebimento

1. Criar rascunho com balança, qualidade, origem e destino.
2. Revisar os dados.
3. Confirmar.
4. Calcular sacas usando o peso da saca da cultura.
5. Criar entrada imutável e atualizar saldo.
6. Registrar auditoria.

### Transferência

1. Informar contexto, origem, destino e quantidade.
2. Bloquear os saldos durante a transação.
3. Validar disponibilidade.
4. Debitar a origem e creditar o destino.
5. Registrar uma movimentação e auditoria.

### Embarque

1. Criar rascunho com comprador, documentos, logística e preço.
2. Validar correspondência com contrato, quando informado.
3. Confirmar.
4. Validar saldo físico e limite contratual.
5. Baixar estoque.
6. Criar conta a receber no Financeiro.
7. Registrar auditoria.

### Estorno

O estorno cria uma movimentação inversa ligada à original. O registro anterior permanece preservado. Em embarques, a conta a receber pendente é cancelada; lançamentos já liquidados exigem tratamento financeiro específico e não são apagados automaticamente.

## Importação de planilhas

Formatos aceitos: CSV, XLSX e XLSM, até 10 MB.

1. validar extensão e tamanho;
2. calcular SHA-256 para evitar duplicidade;
3. ler localmente, sem serviço externo;
4. detectar cabeçalhos por aliases;
5. aplicar mapeamento manual opcional;
6. apresentar prévia e inconsistências;
7. permitir confirmação somente após validação;
8. executar a importação em transação única;
9. manter recebimentos e embarques importados como rascunhos.

Nenhuma planilha é enviada a OCR, IA, armazenamento ou telemetria de terceiros.

## Relatórios

Filtros disponíveis:

- propriedade;
- CAD/PRO;
- talhão;
- cultura;
- safra;
- período;
- local de armazenagem;
- comprador e contrato nos endpoints correspondentes.

Formatos: JSON, CSV, XLSX e PDF. Todos são gerados localmente pelo backend.

## Assistente gerencial

As regras explicáveis usam somente dados internos para:

- comparar safras;
- calcular produtividade por talhão;
- apresentar maior e menor produtividade;
- consolidar estoque disponível;
- destacar maior umidade registrada;
- mostrar utilização de contratos;
- identificar estoque sem cobertura contratual.

As saídas são apoio gerencial e não substituem avaliação agronômica, comercial, contábil ou legal.

## Dependências

- `openpyxl`: leitura e geração local de XLSX/XLSM; licença MIT/Expat.
- `defusedxml`: proteção adicional contra estruturas XML maliciosas; licença PSFL.

Não há API paga, serviço em nuvem, cartão, analytics ou telemetria.
