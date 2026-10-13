# Transportes — versão web (12/10/2026)

## Objetivo e critérios de aceite

Criar uma aba baseada na planilha fornecida, permitindo vários caminhões,
receitas/despesas por data, histórico do motorista, remuneração mensal manual,
ranking de faturamento por placa/motorista e análise de receitas menos custos.
Importação deve ser revisável, atômica e não duplicar nem sobrescrever históricos.
Filtros e exportação devem abranger todos os resultados, independentemente da página.

## Implementação

- Menu **Operações → Transportes**, com Relatórios e ranking, Receitas e despesas,
  Salário e comissão, Caminhões e Importar planilha.
- App Django `apps.transportes`: caminhão com placa única, lançamentos com data,
  motorista histórico, descrição/serviço, origem/destino/local, nota, quantidade,
  unidade e valor unitário; remuneração por caminhão/motorista/competência.
- Maquinas existente registra equipamentos e horímetro, sem placa nem receita de
  frete. Seu comportamento foi preservado; o novo módulo atende o controle da planilha.
- Salário manual em reais e comissão manual em percentual (0 a 100). Comissão
  = máximo(receitas − despesas AREIA/PEDRA, zero) × percentual / 100,
  arredondada a centavos somente ao final, conforme B4/B5/AC15/Z7 da fonte.
  Outros custos entram no saldo, mas não reduzem a base da comissão.
- Cadastros novos usam mês, caminhão e motorista. Remunerações importadas usam
  competência da aba para os lançamentos importados, preservando FEV!A9/A10
  datados em janeiro. Novos lançamentos manuais usam suas datas. Alterar a
  identidade de uma remuneração importada passa a usar o mês do cadastro.
- A API fornece base e comissão calculadas; a tela mostra uma prévia sem gravar,
  percentual, base, comissão em reais e remuneração total. Relatórios/CSV
  recalculam a comissão quando os lançamentos mudam. Notas não controlam o cálculo.
- Nove percentuais existentes recuperados diretamente de B4 da planilha (8%).
  Salários e valores monetários históricos armazenados foram preservados.
  Registros antigos sem percentual preservam o valor histórico e exigem o
  percentual ao editar; nenhum valor em reais é convertido por suposição.
- Total por lançamento: quantidade × valor unitário, arredondado a centavos com
  ROUND_HALF_UP. Despesas totais = despesas operacionais + salário + comissão.
  Saldo = receitas − despesas totais; margem = saldo / receitas × 100, ausente se
  não houver receita. Não se apresenta esse resultado como saldo bancário.
- Remuneração mensal é contabilizada no último dia do mês, sem rateio implícito.
  Datas dos lançamentos são preservadas e determinam os relatórios por período.
- Permissões de consultar/cadastrar/editar/excluir/imprimir integradas ao catálogo
  e à autorização JWT existente. Contas restritas precisam de acesso a Transportes.
- CSV com todos os lançamentos filtrados e resumos/rankings, impressão da aba aberta,
  tabelas com rolagem, proteção contra saída com formulários alterados e cancelamento
  de consultas quando a aba é trocada.

## APIs

- `/api/transportes/caminhoes/`: cadastro/edição; caminhão com histórico protegido
  contra exclusão, podendo ser desativado.
- `/api/transportes/lancamentos/`: cadastro/edição e consulta paginada (30 registros).
- `/api/transportes/remuneracoes/`: salário e comissão manual por competência.
- `/api/transportes/lancamentos/relatorio/`: totais, ranking por placa/motorista,
  resultado mensal e composição por descrição.
- `/api/transportes/lancamentos/exportar/`: CSV filtrado, exige impressão.
- `/api/transportes/lancamentos/previa/` e `importar/`: arquivo `.xlsx` de até 10 MB,
  abas JAN a DEZ; leitura limitada a 50 MB descompactados e linha 1003.
- Filtros de relatório/lancamentos: `data_inicio`, `data_fim`, `caminhao`, `placa`,
  `motorista` (nome exato, sem distinguir maiúsculas/minúsculas).

## Dados carregados e observações da fonte

Após backup verificado e teste de reconciliação isolado, foram carregados 405
lançamentos (178 receitas, 227 despesas), nove remunerações de janeiro a setembro
de 2026 e o caminhão RHD4D04. Nenhum outro módulo financeiro foi alimentado para
evitar duplicação de seus valores.

Totais após arredondamento de cada lançamento: receita R$ 587.530,47; despesas
operacionais R$ 223.319,67; salários R$ 23.359,31; comissões R$ 44.679,05; despesas
totais R$ 291.358,03; saldo R$ 296.172,44.

**Conferir na fonte:** FEV!A9 e FEV!A10 têm data de 31/01/2026. A data foi
preservada, portanto aparecem em janeiro no relatório por data. Não foi feito
ajuste automático para fevereiro. O Excel acumula produtos com mais casas
decimais, enquanto o aplicativo arredonda cada lançamento a centavos; diferenças
de poucos centavos em agregados são possíveis. Descrições vazias recebem rótulo
genérico Frete/Diversos; origem/destino e referência da célula continuam disponíveis.
Unidade não é inferida quando a planilha não diferencia Ton/m³/Km.

Reimportações preservam as posições já importadas. Alterações de valores/textos
em posições existentes são rejeitadas para revisão manual. Remunerações já
existentes não são substituídas. A chave usa placa, motorista, ano, aba e linha;
reorganizar a planilha depois da primeira importação exige revisão.

## Validação e backups

- PostgreSQL isolado: 53 testes de Transportes/accounts aprovados na primeira
  validação; 17 testes finais de Transportes aprovados, incluindo o arquivo real,
  comparação de cada total a centavos e reimportação idempotente.
- `docker compose -p agro-ai-pro exec -T backend python /app/scripts/test_backend_isolado.py apps.transportes apps.accounts`
- `docker compose -p agro-ai-pro exec -T backend python /app/scripts/test_backend_isolado.py apps.transportes`
- Django check aprovado; `makemigrations --check --dry-run` sem mudanças.
- Migration `transportes.0001_initial` aditiva aplicada ao banco local.
- Frontend: testes de componentes, 16 cenários de autenticação, seis cenários de
  rascunhos e usabilidade; TypeScript e Vite via build Docker aprovados.
  O teste de contagem de permissões passou a usar os catálogos de módulos/ações.
- Navegador autenticado: menu Transportes, cadastro de caminhões, lista importada,
  filtro de janeiro combinado com placa/motorista e remuneração mensal conferidos.
  Salário 1.500 e comissão 300 mostraram total 1.800 sem gravação; valores de
  conferência descartados pelo diálogo existente. Campos de data/competência
  ajustados para evento input; filtros leem os valores do formulário no envio.
  Largura móvel 360 px conferida sem transbordamento da página; viewport restaurado.
- Build Windows bloqueado por permissões antigas e falta de Tailwind no
  node_modules local; validação feita no Docker com as dependências do lockfile.
- Backups privados em `D:/PROJETOS/AGRO-AI-PRO/backups/visual-20261012-204449`
  (antes das alterações), `visual-20261012-211314` (antes da migration) e
  `visual-20261012-211638` (antes da carga). Código/alterações locais/uploads,
  dump PostgreSQL, manifesto e hashes SHA-256 preservados; ZIP e catálogo do dump
  verificados. Não houve restauração sobre os dados atuais.
- Trabalho na branch `codex/modernizacao-visual-runtime`, em
  `.worktrees/runtime-origin-main`, que atende os containers existentes.
- Sem commit, push, merge ou publicação em produção.

Impressão física e gravação final do download CSV pelo navegador não foram
verificadas; conteúdo e autorização da exportação foram testados na API.

## Correção da comissão percentual — 12/10/2026

Critérios atendidos: entrada em %, base fiel à fórmula, base negativa zerada,
prévia sem gravação e relatórios com comissão calculada. 19 testes de Transportes
em PostgreSQL isolado aprovados; testes frontend, TypeScript e Vite aprovados.
Migrations 0002/0003 aditivas aplicadas. Django check e consistência de migrations
verificados. Backups íntegros: visual-20261012-215357 e visual-20261012-215626.
Arquivos alterados: models, serializers, importacao, relatorios, views, tests,
migrations de Transportes; API e página React; esta decisão e docs/SPRINTS.md.
Sem commit, push ou merge. Arquivo Excel original preservado.

Conferência autenticada: campo Comissão manual (%), nove linhas com 8%, base
de fevereiro R$ 68.355,86, comissão 8% R$ 5.468,47 e simulação 12%
R$ 8.202,70, sem gravação. Backend/frontend locais saudáveis.

## Telas separadas e rolagem livre — 12/10/2026

Formulários de Transportes usam position: static; não cobrem os dados ao rolar.
Receitas/despesas: inserção em aba própria e consulta em Receitas e despesas.
Salário/comissão: formulário separado da nova aba Dados por motorista / placa.
Consulta de remunerações com filtros por motorista e caminhão no servidor,
agrupamento da página por motorista ou placa e paginação de 30 registros.
Salvar abre a consulta; editar abre o formulário, preservando a proteção de
alterações não salvas. Cálculos e dados persistentes não foram alterados.
Arquivos: página, CSS e API de Transportes, esta decisão e SPRINTS.
Testes frontend, TypeScript/Vite aprovados via Docker. Backup verificado:
D:/PROJETOS/AGRO-AI-PRO/backups/visual-20261012-220510.

Conferência autenticada: formulário de remuneração sem tabela e position static;
inserção de receitas/despesas sem tabela e position static; consulta sem formulário.
Agrupamento por motorista e placa, filtro RHD4D04 com nove registros,
filtro RHS3E18 vazio confirmado. Nenhuma gravação operacional na conferência.

## Legibilidade da impressão — 12/10/2026

Fonte das tabelas aumentada de 9pt para 11pt, texto 12pt e títulos 16pt.
Página nomeada transportes em A4 paisagem, margens 12mm, cabeçalhos repetidos,
linhas sem divisão entre páginas, data/quantidade/valores sem quebra, coluna
placa/motorista com largura mínima 35mm. Ajuda da consulta omitida no papel.
Regras restritas ao módulo. Alterados transportes.css e TransportesPage.tsx.
Frontend/testes/TypeScript/Vite e revisão de diff aprovados; impressão física
não verificada. Backup íntegro visual-20261012-221238; sem alteração de dados.

## Impressão compacta — 12/10/2026

Após conferência da imagem do usuário, reduzido padding vertical de 3mm para
0,8mm, entrelinha de 1,35 para 1,15, tabela 10,5pt, motorista 9,5pt em coluna
mais larga (52mm/22%). Margens 10mm e título 14pt com menor distância da tabela.
Referência auxiliar da célula Excel omitida apenas no papel; dados preservados.
Critério: reduzir altura das linhas e quebras do nome, mantendo datas/valores
legíveis. Frontend/testes/TypeScript/Vite e diff aprovados. Impressão física e
contagem final de linhas por folha não verificadas; variam pelo conteúdo.
Backup verificado visual-20261012-223229. Sem alteração de banco ou operações Git.
