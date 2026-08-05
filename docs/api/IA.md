# API do Assistente

`GET /api/ai/insights/` exige JWT e aceita `propriedade` e `safra`.

A resposta informa método, momento de geração, aviso de responsabilidade e uma
lista ordenada por criticidade. Cada insight contém código, nível, título,
evidência, recomendação e módulo. O método `regras_explicaveis_v1` é
determinístico e não compartilha dados com serviços externos.

## Regras de grãos

O Assistente Agrícola V1 também consulta o ledger oficial do módulo de grãos e
pode apresentar:

- saldo consolidado por propriedade e safra;
- lotes inativos que ainda possuem saldo;
- armazéns ativos com ocupação igual ou superior a 90%;
- inconsistências quando um lote apresenta saldo negativo no ledger.

A ocupação considera todo o saldo físico do armazém, mesmo quando a consulta é
filtrada por safra, porque a capacidade é compartilhada entre todos os lotes.
Saldos negativos não compensam saldos positivos no cálculo da ocupação: eles
são desconsiderados nesse cálculo e geram um alerta crítico explícito para
conferência das movimentações e do estoque físico.
As regras são operacionais e explicáveis; não classificam qualidade de grãos
nem substituem conferência física ou orientação profissional.
