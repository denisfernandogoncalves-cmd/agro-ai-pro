# Controle multiusuário por propriedade

## Modelo de autorização

O AGRO-AI-PRO usa `AcessoPropriedade` para relacionar usuários e propriedades.
Cada vínculo possui um dos papéis abaixo:

- **Administrador:** gerencia a propriedade, usuários e todos os registros.
- **Gestor:** cria e altera cadastros e registros gerenciais, sem administrar acessos.
- **Operador:** registra e executa operações agrícolas, movimentações de estoque e
  históricos operacionais.
- **Somente leitura:** consulta dados, relatórios e insights sem alterar registros.

Superusuários Django mantêm acesso administrativo completo.

A API filtra os querysets antes de localizar objetos. Assim, a tentativa de abrir
diretamente um ID pertencente a outra propriedade retorna HTTP 404. Tentativas de
alteração dentro de uma propriedade autorizada, mas incompatíveis com o papel,
retornam HTTP 403.

## Estratégia para dados existentes

A migration `0004_acessopropriedade` não altera nem remove registros existentes.
Ela cria a tabela de vínculos e associa automaticamente todos os superusuários
existentes a todas as propriedades com o papel de administrador.

Registros antigos sem propriedade continuam preservados, mas ficam visíveis
somente para superusuários até serem vinculados a uma propriedade. Essa decisão
evita exposição acidental entre usuários.

## Vinculação inicial

Pelo Django Admin:

1. Abra **Administração > Acessos a propriedades**.
2. Escolha a propriedade e o usuário.
3. Defina o papel.
4. Mantenha o vínculo ativo.

Pela API, um administrador da propriedade pode usar:

```http
POST /api/propriedades/acessos/
Content-Type: application/json

{
  "propriedade": 1,
  "usuario": 2,
  "papel": "gestor",
  "ativo": true
}
```

Antes de liberar contas comuns, confirme que todas as propriedades possuem ao
menos um administrador ativo e revise os registros antigos sem propriedade.

## Mercado

Cotações, clima do Corn Belt e notícias de mercado continuam globais porque não
possuem vínculo com propriedades. Dados de mercado que futuramente receberem
uma propriedade deverão usar a mesma camada central de escopo.
