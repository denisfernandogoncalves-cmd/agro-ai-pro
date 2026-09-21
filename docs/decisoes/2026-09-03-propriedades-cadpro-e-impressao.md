# Propriedades com CAD/PRO e grade de impressão

**Data:** 03/09/2026
**Escopo:** identificação de propriedades no frontend e impressão da aba Propriedades

## Contexto

Os seletores exibiam somente o nome da propriedade, obrigando o usuário a
consultar outro campo para confirmar o CAD/PRO. Na impressão da aba
Propriedades, cada cadastro também ocupava toda a largura da página.

## Decisão

- Todo seletor alimentado pelo cadastro de propriedades passa a apresentar o
  padrão `Nome — CAD/PRO número`.
- Quando uma propriedade possuir mais de um CAD/PRO, todos os números são
  exibidos no mesmo rótulo.
- Quando não houver número cadastrado, o rótulo informa
  `CAD/PRO não informado`.
- A seleção de propriedades no rateio de Cargas colhidas adota o mesmo padrão.
- Na impressão da aba Propriedades, os cartões são distribuídos em duas
  colunas. A interface normal continua com o layout original.

## Implementação

O formatador compartilhado `rotuloPropriedade` fica na API de propriedades e é
reutilizado pelos módulos. A grade de duas colunas é aplicada somente em
`@media print`, por classes específicas da aba Propriedades.

## Validação

- teste unitário do rótulo com um, vários ou nenhum CAD/PRO;
- renderização dos seletores de Talhões e Clima;
- verificação estrutural da grade de impressão;
- suíte de componentes, autenticação e build do frontend.
