# Gestão da Produção Agrícola

## Status

Módulo oficial do AGRO-AI-PRO, aprovado para substituir as planilhas de controle físico, fiscal e comercial da produção agrícola.

A primeira entrega da modernização do frontend registra o módulo na navegação e na arquitetura, sem criar dados simulados. A implementação transacional será realizada em etapa própria, com models, migrations, APIs, serviços, permissões e testes específicos.

## Fronteira de domínio

O app existente `apps.producao` permanece responsável por **operações agrícolas de campo**: preparo, plantio, adubação, pulverização, irrigação, colheita, custos e consumo de insumos.

A nova **Gestão da Produção** será um contexto separado, planejado como `apps.gestao_producao`, para evitar:

- quebra das APIs atuais de Operações;
- mistura entre atividades de campo e estoque comercial de grãos;
- reutilização indevida do estoque de insumos;
- duplicação de saldos, documentos e regras fiscais.

## Integrações obrigatórias

O módulo deverá referenciar, sem duplicar cadastros:

- `Propriedade` para titularidade e escopo multiusuário;
- `Talhao` para origem e produtividade;
- parceiros/clientes do Financeiro para compradores, terceiros e transportadores;
- `LocalEstoque` quando o cadastro físico for compatível, adicionando uma especialização de armazenagem de grãos quando necessário;
- lançamentos financeiros gerados pelos embarques confirmados;
- geometrias de propriedades e talhões para o mapa;
- cotações do Mercado para apoio à comercialização;
- camada de insights para alertas e análises explicáveis.

## Entidades planejadas

### CAD/PRO

Cada propriedade poderá possuir um ou mais registros CAD/PRO ativos.

Campos mínimos:

- propriedade;
- número/identificador;
- titular;
- situação;
- vigência;
- observações;
- auditoria de criação e alteração.

Toda produção própria deverá estar vinculada a propriedade, CAD/PRO, cultura e safra.

### Cultura e safra

A cultura deverá usar um catálogo compartilhado e estável. A safra continuará representada pelo padrão já utilizado no sistema, com validação centralizada para evitar formatos divergentes.

### Recebimento de produção

Cada carga deverá registrar:

- data e hora;
- motorista e placa;
- propriedade e CAD/PRO;
- talhão;
- cultura e safra;
- peso bruto;
- umidade;
- impureza;
- defeitos;
- descontos calculados;
- peso líquido;
- quantidade equivalente em sacas;
- local de armazenagem;
- origem própria ou de terceiro;
- documentos e observações;
- usuário responsável e trilha de auditoria.

O peso líquido e a quantidade em sacas deverão ser calculados por serviço de domínio, com parâmetros versionados e resultado auditável. Valores calculados não poderão depender apenas do frontend.

### Estoque físico de grãos

O estoque de grãos será controlado por livro-razão imutável. O saldo será derivado das movimentações confirmadas, evitando edição direta de quantidade.

Dimensões mínimas do saldo:

- propriedade;
- CAD/PRO;
- cultura;
- safra;
- local de armazenagem;
- titularidade própria ou de terceiro;
- qualidade/lote quando aplicável.

Movimentos previstos:

- recebimento;
- ajuste autorizado;
- transferência de saída;
- transferência de entrada;
- embarque;
- devolução;
- cancelamento por estorno compensatório.

### Transferências

Transferências entre silos, armazéns, propriedades e CAD/PRO deverão ser atômicas: a saída e a entrada serão confirmadas na mesma transação. Falha em qualquer etapa deverá cancelar toda a operação.

### Contratos

Campos mínimos:

- comprador;
- propriedade/CAD/PRO vendedor;
- cultura e safra;
- quantidade contratada;
- unidade;
- preço e moeda;
- período de entrega;
- tolerâncias;
- situação;
- quantidade embarcada;
- saldo contratual;
- documentos e auditoria.

O saldo do contrato será derivado dos embarques confirmados.

### Embarques

Cada embarque deverá registrar:

- comprador e destino;
- contrato;
- nota do produtor;
- nota da empresa;
- motorista e placa;
- romaneio;
- propriedade, CAD/PRO, cultura e safra;
- local de origem;
- quantidade;
- preço;
- valor;
- usuário responsável;
- data de confirmação.

A confirmação deverá executar em uma única transação:

1. validar saldo físico;
2. validar saldo do CAD/PRO;
3. validar saldo contratual;
4. registrar a saída do estoque de grãos;
5. atualizar os saldos derivados;
6. registrar auditoria;
7. criar o lançamento financeiro correspondente;
8. impedir nova confirmação do mesmo embarque.

Cancelamentos após confirmação deverão gerar estornos rastreáveis, nunca apagar movimentos históricos.

### Terceiros e notas fiscais

A produção de terceiros deverá manter titularidade separada do estoque próprio. Notas fiscais e documentos deverão ser relacionados aos recebimentos, transferências e embarques sem duplicar dados de parceiros já existentes.

## Segurança multiusuário

O módulo deverá usar a camada da PR #16:

- superusuário com acesso completo;
- administrador com administração da propriedade e vínculos;
- gestor com operações gerenciais;
- operador com recebimentos, transferências e embarques permitidos;
- somente leitura sem ações de escrita;
- filtros de queryset antes da busca por ID;
- HTTP 404 para objetos fora do escopo;
- HTTP 403 para ações incompatíveis com o papel;
- propriedade e CAD/PRO validados no backend em toda operação.

A interface apenas refletirá permissões retornadas pela API. A proteção principal permanecerá no backend.

## Auditoria

Eventos críticos deverão armazenar:

- usuário;
- data e hora;
- ação;
- entidade e identificador;
- estado anterior e posterior quando permitido;
- motivo;
- origem da requisição;
- vínculo com recebimento, transferência, contrato, embarque ou documento.

Registros financeiros e movimentos físicos confirmados deverão ser imutáveis, com correções por estorno.

## Relatórios

Filtros obrigatórios:

- propriedade;
- CAD/PRO;
- talhão;
- cultura;
- safra;
- período;
- comprador;
- contrato;
- motorista;
- placa;
- local de armazenagem;
- titularidade própria ou de terceiro.

Relatórios mínimos:

- produção recebida;
- descontos de qualidade;
- produtividade por talhão;
- posição de estoque;
- movimentações e transferências;
- saldo por CAD/PRO;
- contratos e saldo a entregar;
- embarques;
- notas fiscais;
- receitas integradas;
- trilha de auditoria.

## Dashboard

Indicadores previstos:

- produção total;
- produção por propriedade;
- produção por CAD/PRO;
- produtividade por talhão;
- estoque físico;
- saldo disponível;
- produção de terceiros;
- embarques;
- contratos e saldo contratual;
- receitas;
- alertas de qualidade e consistência.

Enquanto as APIs não existirem, o frontend deverá ocultar os números ou exibir estado vazio informativo. Dados não poderão ser inventados.

## Mapa

A camada de mapa agrícola deverá aceitar futuramente:

- propriedades;
- talhões;
- pontos ou áreas de produção;
- silos e locais de armazenagem;
- filtros por cultura, safra, CAD/PRO e titularidade.

A primeira entrega prepara os tipos de camada `producao` e `armazenagem`, sem integrar serviços externos ou pagos.

## Inteligência artificial

Os insights deverão ser explicáveis e baseados em dados internos:

- comparativo entre safras;
- previsão de estoque disponível;
- produtividade por talhão;
- propriedades com melhor desempenho;
- alertas de umidade elevada;
- alertas de estoque baixo;
- contratos próximos do limite;
- sugestões de comercialização considerando estoque, contratos e cotações.

Sugestões comerciais deverão indicar evidências, premissas e limitações. Não deverão executar vendas automaticamente.

## Sequência recomendada de implementação

1. descoberta e importação das planilhas atuais;
2. dicionário de dados e regras de cálculo;
3. CAD/PRO, culturas, locais e permissões;
4. recebimentos e qualidade;
5. livro-razão de estoque de grãos;
6. transferências;
7. contratos e terceiros;
8. embarques, notas e integração financeira;
9. relatórios, dashboard e mapa;
10. insights e migração assistida das planilhas;
11. homologação paralela e encerramento controlado das planilhas.

## Critérios de substituição das planilhas

As planilhas somente serão descontinuadas após:

- conciliação de saldos;
- importação validada;
- rastreabilidade por documento;
- testes de cálculos de qualidade;
- testes de concorrência e saldo insuficiente;
- homologação por propriedade e CAD/PRO;
- relatórios equivalentes ou superiores;
- plano de reversão e backup;
- aprovação formal do usuário responsável.
