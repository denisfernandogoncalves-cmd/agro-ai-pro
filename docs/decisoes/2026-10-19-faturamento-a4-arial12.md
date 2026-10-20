# Faturamento: A4 retrato e Arial 12

Solicitação de 19/10/2026, com preferência final por Arial 12.

Impressão do navegador em A4 retrato, margem de 14 mm e Arial 12 em todo o relatório. Propriedades em blocos com rótulos, sem reduzir a fonte para caber. PDF com Arial regular/negrito incorporada em 12 pontos, campos em duas colunas, totais juntos e paginação.

Excel com todas as abas em A4 retrato, Arial 12, escala de 100%, quebra de texto e altura de linha ajustada. A aba inicial `Impressão` organiza os dados em duas colunas e separa propriedades por quebras de página. Abas tabulares preservadas para consulta; tabelas largas podem ocupar mais de uma página horizontal se impressas diretamente, portanto usar `Impressão` para o relatório.

Dados continuam vindo do resumo histórico, sem apelidos. Sem migrations ou alterações em dados de negócio e permissões.

## Fontes locais

O PDF exige `arial.ttf` e `arialbd.ttf`, procurando em `AGRO_ARIAL_DIR`, `/app/.fonts`, `.fonts` na raiz ou `C:/Windows/Fonts`. Ambiente local configurado com cópias das fontes licenciadas do Windows em `.fonts/`, ignoradas pelo Git. Novas instalações precisam fornecer essas fontes; arquivos proprietários não são distribuídos no repositório. Sem substituição silenciosa por Helvetica.

SHA-256 regular: `B3658EADAE55E682B5F69EB64C439C1ECC8F196C0BB8D4756D145D13BC86476A`.
SHA-256 negrito: `E8F4E3BAF6CC35FED6FCCE3A540E8B39E8F6CDA1D22A28F2EC8F526FEF7A43F5`.

## Verificação

- Backup: `D:/PROJETOS/AGRO-AI-PRO/backups/visual-20261019-090002`, código, banco e uploads, manifesto e integridade verificados.
- 29 testes de faturamento/identificação/coordenadas aprovados; três testes de PDF/Excel aprovados após a revisão final. Dimensões A4, fontes Arial 12 incorporadas, conteúdo, limites da página e configuração do XLSX conferidos.
- Testes frontend, TypeScript e Vite aprovados pelo build Docker.
- PDF demonstrativo renderizado e conferido visualmente com BEP e identificação principal/secundária. Impressão física e renderização pelo Microsoft Excel não executadas.
- Diff sem erros de espaço; frontend atualizado na porta 5174, `/api/ready/` retorna `ok`.

## Revisão solicitada: agrupamento em linhas

Após a conferência do usuário, a impressão, o PDF e a aba `Impressão` do Excel passaram a apresentar uma propriedade por linha de tabela. Produtor e coordenadas ficam na célula da propriedade; identificação e BEP, quando aplicável, na célula CAD/PRO. Área, embalagens e quantidade ficam lado a lado. A4 retrato, Arial 12 e os dados históricos foram preservados. Isso substitui a organização vertical por propriedade descrita acima.

Backup anterior: `D:/PROJETOS/AGRO-AI-PRO/backups/visual-20261019-090910`, código, banco e uploads com integridade verificada. Quatro testes de formatação PDF/Excel aprovados; testes frontend e build TypeScript/Vite aprovados. PDF demonstrativo conferido visualmente. Sem migrations, commit ou push.

## Revisão: cabeçalho compacto e coordenadas na mesma linha

Produto aparece primeiro, destacado, seguido pelos totais de embalagens e quantidade em negrito e fundo de destaque. Empresa, envio, safra, apresentação e dosagem ficam em um cabeçalho compacto, preservando os valores e a organização em linhas por propriedade.

Latitude e longitude ficam na mesma linha. Somente as coordenadas usam fonte menor: 7 pontos na impressão do navegador e no Excel; no PDF, ajuste proporcional até 9 pontos para caber na célula. Os demais dados continuam em Arial 12 e A4 retrato. Excel usa texto rico na célula da propriedade para preservar nome/produtor em 12 pontos.

Backup: `D:/PROJETOS/AGRO-AI-PRO/backups/visual-20261019-122721`, verificado antes da alteração. Cinco testes de formatação PDF/Excel, testes frontend e build TypeScript/Vite aprovados. Conferência visual do PDF com coordenadas GMS e identificação CAD/PRO. Impressão física/Microsoft Excel não executados. Sem migrations nem alterações dos registros históricos.

## Revisão: resumo em duas linhas

Primeira linha: produto, total de embalagens e quantidade total, em negrito. Segunda linha: empresa, data, safra, apresentação e dosagem. Aplicado à tela/impressão, PDF e aba de impressão do Excel. Exemplo ANKOR/AGRO PRODUZ conferido em duas linhas, mantendo Arial 12; textos excepcionalmente extensos quebram naturalmente sem cortes. Coordenadas continuam na mesma linha e com fonte menor.

Backup verificado: `D:/PROJETOS/AGRO-AI-PRO/backups/visual-20261019-220638`. Seis testes de formatação aprovados, inclusive verificação das duas linhas do PDF; frontend, TypeScript e Vite aprovados. PDF renderizado para conferência. Sem migrations ou alterações de dados.

## Revisão: propriedade/produtor mais largos e embalagens por extenso

Coluna de propriedade/produtor ampliada de 68 para 82 mm no PDF e de 37% para 45% na impressão; aba de impressão do Excel também ampliada. Cabeçalho e total do PDF agora apresentam, por exemplo, `Total de embalagens: 7 BALDES DE 20 LITROS`. Singular/plural para embalagens conhecidas e unidades por extenso, preservando nomes personalizados desconhecidos e os valores do resumo histórico.

Nome do produto segue primeiro, sem rótulo redundante, para preservar o cabeçalho compacto em duas linhas. Apresentação removida da segunda linha pois já consta no total detalhado. A4 retrato e Arial 12 preservados; coordenadas na mesma linha.

Backup: `D:/PROJETOS/AGRO-AI-PRO/backups/visual-20261019-221229`, código/banco/uploads verificados. Sete testes PDF/Excel, testes frontend, TypeScript/Vite e revisão de diff aprovados; PDF conferido visualmente com exemplo de produtor longo. Sem migrations ou alterações nos dados existentes.
