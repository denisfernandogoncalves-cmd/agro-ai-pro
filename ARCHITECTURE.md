# Arquitetura do AGRO-AI-PRO

## Visão geral

O AGRO-AI-PRO é um ERP agrícola modular. A arquitetura separa domínio, serviços transacionais, APIs e apresentação, mantendo as regras de autorização no backend e reutilizando entidades compartilhadas entre módulos.

## Componentes

- **Backend:** Django 5 e Django REST Framework
- **Autenticação:** JWT com Simple JWT
- **Frontend:** React 19, Vite e TypeScript
- **Mapas:** React Leaflet e OpenStreetMap
- **Banco:** PostgreSQL 17
- **Cache:** Redis, com fallback local
- **Infraestrutura:** Docker Compose e Nginx
- **Testes:** SQLite em memória para a suíte automatizada e PostgreSQL no ambiente Docker

## Camadas do backend

### Models

Representam os agregados e as restrições persistentes. Relacionamentos operacionais usam `PROTECT` quando a exclusão colocaria a rastreabilidade em risco.

### Serializers

Validam contratos HTTP e executam `full_clean` nos modelos relevantes. Campos calculados, autoria e vínculos transacionais são somente leitura.

### Services

Concentram transações que alteram múltiplos agregados. Confirmações, movimentações e estornos utilizam `transaction.atomic` e bloqueio de linhas para impedir concorrência e saldo negativo.

### ViewSets e APIs

Aplicam autenticação, filtros, busca, ordenação, papéis e escopo antes de localizar os objetos. IDs externos ao escopo retornam HTTP 404; operações incompatíveis com o papel retornam HTTP 403.

### Relatórios e insights

Leem os mesmos agregados operacionais. Não mantêm bases paralelas nem duplicam saldos.

## Autorização

A autorização possui duas dimensões:

1. `AcessoPropriedade`, com administrador, gestor, operador e somente leitura;
2. `AcessoCadPro`, para restringir usuários comuns aos CAD/PRO autorizados.

Superusuários mantêm acesso completo. Administradores de uma propriedade acessam todos os seus CAD/PRO. Gestores, operadores e usuários de leitura precisam de vínculo explícito ao CAD/PRO.

A interface oculta comandos incompatíveis, mas o backend permanece como fonte de verdade.

## Gestão Integrada da Produção

O domínio de produção reutiliza:

- `Propriedade` e `Talhao` para origem produtiva;
- `ParceiroFinanceiro` para compradores, transportadores e terceiros;
- `LocalEstoque` para silos, armazéns e locais externos;
- `LancamentoFinanceiro` para receitas de embarques;
- permissões centrais de `apps.core`.

### Agregados próprios

- `Cultura`
- `Safra`
- `CadPro`
- `AcessoCadPro`
- `Motorista`
- `Veiculo`
- `RecebimentoProducao`
- `SaldoGraos`
- `MovimentacaoGraos`
- `ContratoProducao`
- `EmbarqueProducao`
- `AuditoriaProducao`
- `ImportacaoPlanilha`

O estoque de grãos é separado do estoque de insumos porque exige dimensões produtivas e comerciais próprias. A unidade canônica é quilograma; sacas são calculadas usando o peso configurado na cultura.

### Livro-razão de grãos

`MovimentacaoGraos` registra entradas, saídas, transferências, ajustes e estornos. `SaldoGraos` é uma projeção transacional por propriedade, CAD/PRO, talhão, cultura, safra e local. A restrição de banco e os serviços impedem valores negativos.

### Recebimento

Um recebimento permanece editável enquanto está em rascunho. A confirmação cria a entrada no estoque, calcula sacas, registra autoria e auditoria. O sistema armazena os percentuais informados, mas não inventa regras de desconto de qualidade.

### Embarque

A confirmação valida estoque e contrato, cria a saída de grãos, calcula sacas e valor total e gera uma conta a receber no Financeiro. Estornos são movimentos inversos; registros confirmados não são apagados.

### Importação legada

A importação aceita CSV, XLSX e XLSM. O fluxo é: upload, detecção de colunas, mapeamento manual opcional, prévia, inconsistências e confirmação transacional. Nenhum dado é importado apenas pelo upload.

## Frontend Enterprise

O frontend utiliza:

- `AppShell` responsivo com sidebar fixa, recolhível e drawer móvel;
- cabeçalho com usuário, papel, propriedade, safra e tema;
- design tokens e temas claro/escuro persistidos;
- componentes compartilhados de cartões, tabelas, filtros, loading, erro e permissões;
- módulos carregados com `React.lazy` e `Suspense`;
- mapa agrícola reutilizável para propriedades e talhões;
- páginas legadas preservadas dentro do novo shell.

## Integrações

As integrações internas usam serviços e chaves estrangeiras, não replicação de dados:

- Produção → Estoque de grãos
- Embarque → Financeiro
- Produção → Relatórios
- Produção → Assistente IA
- Produção → Geoprocessamento por propriedade e talhão
- Estoque e contratos → apoio à comercialização

## Decisões de segurança e integridade

- autenticação é obrigatória por padrão;
- operações financeiras e de estoque são atômicas;
- registros de auditoria são somente leitura;
- arquivos de importação são limitados por tamanho e extensão;
- APIs externas não recebem dados operacionais;
- nenhum serviço pago é necessário para esta implementação;
- migrations criam estruturas novas sem apagar registros existentes.
