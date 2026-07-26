# API do Assistente

`GET /api/ai/insights/` exige JWT e aceita `propriedade`.

A resposta informa método, momento de geração, aviso de responsabilidade e uma
lista ordenada por criticidade. Cada insight contém código, nível, título,
evidência, recomendação e módulo. O método `regras_explicaveis_v1` é
determinístico e não compartilha dados com serviços externos.
