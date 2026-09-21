# Impressão de Vendas em formato de planilha

Solicitação do Product Owner em 31/08/2026: imprimir o controle de Vendas com
layout semelhante à planilha operacional apresentada como referência.

## Resultado

- a impressão do módulo Vendas usa A4 em orientação retrato e margem de 1 cm;
- o cabeçalho geral é ocultado em Vendas para manter título e tabela juntos na
  primeira página;
- somente o quadro de saídas é impresso, sem formulários, cartões ou ações;
- título, resumo e cabeçalhos usam fundo verde-claro e grade com bordas pretas;
- cada entrega ativa ocupa uma linha;
- as colunas são Data, Destino, Placa, CAD/PRO, Contrato, nota do produtor,
  nota da empresa, peso líquido e quantidade em sacas de 60 kg;
- datas são exibidas em `dd/mm/aaaa`;
- peso líquido usa três casas decimais e sacas usam duas casas decimais;
- o CAD/PRO impresso identifica propriedade, número e proprietário;
- a tela interativa permanece com seus controles e motorista, sem alteração da
  regra de negócio ou dos dados persistidos.
- o formulário de nova venda ocupa a largura da página, usa campos horizontais
  e rola normalmente com a página; as vendas registradas aparecem abaixo dele;
- o quadro de controle em formato de planilha fica oculto na tela interativa e
  é exibido somente na impressão; uma aba própria poderá ser criada futuramente;
- em telas estreitas, o formulário volta ao fluxo vertical.

Os demais módulos continuam usando o layout A4 retrato existente.

## Segurança e validação

Antes da alteração foi criado e validado o backup privado
`backups/retomada-2026-08-31-215017-330013/`, contendo código, banco PostgreSQL,
uploads, estado Git, catálogo e hashes SHA-256. Nenhum backup anterior foi
sobrescrito e nenhuma restauração foi realizada.

Validações executadas:

- `npm.cmd test`: 40 testes de componentes e 13 de autenticação aprovados;
- `npm.cmd run build`: TypeScript e Vite aprovados;
- `git -c core.safecrlf=false diff --check`: aprovado.

Permanece apenas o aviso preexistente do Vite sobre o bundle principal maior que
500 kB. Não houve migration, alteração de banco, commit, push ou merge.
