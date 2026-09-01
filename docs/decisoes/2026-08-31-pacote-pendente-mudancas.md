# Pacote MUDANÇAS — autorizado em 01/09/2026

Solicitação registrada pelo Product Owner em 31/08/2026 e autorizada pelo
comando **MUDANÇAS** em 01/09/2026.

## 1. Descongelar painel de transferência

- O formulário/painel de **Transferência de saldo entre CAD/PROs** deve rolar
  normalmente com a página.
- Ele não deve permanecer fixo no topo nem possuir rolagem interna própria.
- A organização atual por Cultura, Ano/Safra, origem e destino deve ser mantida.

## 2. Imagem de satélite nos mapas

- Disponibilizar uma camada de imagem de satélite nos mapas de propriedades e
  talhões.
- Preservar os limites desenhados, marcadores, seleção e cálculo de área sobre a
  imagem.
- Permitir alternar entre mapa convencional e satélite.
- Antes da implementação, verificar licença, atribuição, limites de uso, chave
  de API, privacidade e eventual custo do provedor. Não contratar serviço nem
  inserir credencial sem autorização do Product Owner.

## 3. Unidade oficial: alqueire paulista

- Adotar **alqueire paulista** como unidade de área apresentada ao usuário em
  todo o programa.
- Conversão oficial informada pelo Product Owner:

  `1 alqueire paulista = 2,42 hectares`

- Entradas, telas, cartões, mapas, filtros, totais, indicadores, exportações e
  impressões devem apresentar área em alqueires paulistas.
- A estratégia de armazenamento deve preservar precisão e dados históricos. A
  opção preferencial a avaliar na implementação é manter uma unidade canônica
  no banco e converter apenas nas fronteiras de entrada e saída, evitando uma
  migration destrutiva ou arredondamentos acumulados.
- Identificar e testar todos os pontos que atualmente usam `ha`, `hectare`,
  `hectares`, `area_ha` ou cálculos derivados de área.

## 4. Relatório de produção por propriedade e CAD/PRO

- Em **Relatórios**, permitir consultar e imprimir produção agrupada por
  Propriedade e CAD/PRO.
- Permitir filtros, no mínimo, por Cultura e Ano/Safra.
- Exibir, quando houver dados de origem suficientes:
  - propriedade;
  - CAD/PRO;
  - área em alqueires paulistas;
  - quantidade total em kg;
  - quantidade em sacas de 60 kg;
  - quantidade em outros locais de armazenagem;
  - quantidade destinada a semente;
  - média de sacas de 60 kg por alqueire paulista.
- A média deve ser calculada como `sacas de 60 kg / área em alqueires` e deve
  tratar área zero ou ausente sem divisão inválida.
- Totais devem respeitar exatamente os filtros aplicados e não podem duplicar
  produção por causa de relacionamentos entre propriedade, CAD/PRO, posição ou
  movimentação.

## 5. Impressões configuráveis e somatórios

- Antes de imprimir, permitir ao usuário escolher quais informações/colunas
  serão incluídas.
- A prévia e a impressão devem refletir a mesma seleção.
- Exibir somatórios das colunas numéricas selecionadas e totais coerentes com os
  filtros ativos.
- Para médias e índices, calcular o total correto a partir dos agregados; não
  usar média simples de médias quando isso distorcer o resultado.
- Manter título, cabeçalho, relatório e totais juntos sempre que couberem na
  primeira página, sem criar uma página isolada apenas para o título.
- Preservar A4 retrato como padrão atual, oferecendo orientação diferente apenas
  quando necessária para as colunas escolhidas.
- A configuração de colunas deve ser clara, reversível e não alterar os dados
  persistidos do relatório.

## Critérios gerais para a futura execução

- Criar e validar novo backup antes de iniciar a implementação e antes de
  qualquer migration ou alteração de dados.
- Fazer inventário de impacto em frontend, backend, API, banco, relatórios,
  mapas, testes e documentação.
- Preservar todos os dados atuais e mudanças não commitadas.
- Criar migrations apenas se necessárias e ensaiá-las com cópia isolada do
  banco antes de aplicá-las ao ambiente atual.
- Validar conversões com casos conhecidos, incluindo `2,42 ha = 1,00 alqueire`.
- Validar os totais e a produtividade do relatório com cálculos independentes.
- Executar testes, lint, build, verificação de migrations, revisão do diff e
  verificação visual das telas e impressões.
- Não publicar em produção, não fazer merge e não remover dados sem autorização
  explícita.

## Referências visuais recebidas

- painel de Transferência de saldo a descongelar;
- mapa de talhão com camada cartográfica, para inclusão de satélite;
- planilha de produção por propriedade em alqueires, kg, sacas e média por
  alqueire;
- prévia de impressão de Vendas com cabeçalho e tabela.

## Implementação autorizada

- painel de transferência descongelado por regra específica de layout;
- mapas de propriedade e talhão com satélite como camada inicial e alternância
  para o mapa convencional;
- alqueire paulista adotado nas entradas e apresentações de área, mantendo
  hectares como unidade canônica interna para preservar os dados existentes;
- conversão central `1 alqueire paulista = 2,42 hectares`;
- novo relatório **Produção por Propriedade/CAD-PRO**, agrupado também por
  cultura e safra, com área, kg, sacas, armazenagem externa, semente e média;
- seleção reversível das colunas apresentadas e impressas;
- linha de somatórios calculada sobre todos os resultados filtrados, com média
  total ponderada por área.

Não foi necessária migration nem conversão destrutiva do banco.
