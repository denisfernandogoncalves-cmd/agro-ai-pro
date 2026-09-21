# Otimização da impressão de Cadastros agrícolas

**Data:** 03/09/2026
**Escopo:** impressão da aba Cadastros agrícolas

## Contexto

A impressão reutilizava o fluxo vertical da tela. Os registros de contratos,
armazenagens, depósitos, produtos e fornecedores ocupavam toda a largura da
folha, gerando páginas longas e com muito espaço vazio.

## Decisão

- usar A4 paisagem, conforme a regra geral para impressões largas;
- manter cada tipo de cadastro como uma linha/seção identificada;
- distribuir os registros de cada seção em três colunas;
- aplicar bordas e espaçamento compacto para separar cada registro;
- ocultar formulários, botões e o controle de histórico na impressão;
- preservar integralmente o layout interativo da tela.

## Validação

- teste estrutural da classe exclusiva da aba;
- teste da grade de três colunas dentro de cada seção;
- suíte de componentes e autenticação;
- build TypeScript/Vite.
