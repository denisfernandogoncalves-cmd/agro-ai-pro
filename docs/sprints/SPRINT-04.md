# Sprint 4 — Clima

**Status:** concluída
**Conclusão registrada em:** 25/07/2026

## Objetivo

Disponibilizar previsão meteorológica por propriedade, com persistência,
consulta histórica, indicadores úteis à operação agrícola e tratamento seguro
da integração externa.

## Entregas

- previsão de sete dias por propriedade com coordenadas;
- temperaturas mínima e máxima;
- chuva acumulada e probabilidade de precipitação;
- umidade relativa média e vento máximo;
- condição meteorológica baseada nos códigos WMO;
- alertas de geada, calor, chuva intensa, vento forte e baixa umidade;
- histórico idempotente por propriedade e data;
- filtros por propriedade e intervalo de datas;
- interface responsiva para consulta e atualização;
- autenticação JWT em todos os endpoints;
- tratamento de timeout, erro HTTP e resposta inconsistente;
- integração gratuita com Open-Meteo, sem chave de API.

## Arquitetura

O endpoint externo é consultado somente quando o usuário solicita atualização.
O backend persiste os resultados com `update_or_create`, garantindo uma única
previsão por propriedade e data. Leituras da interface usam os dados locais e
não dependem da disponibilidade imediata do provedor.

O transporte HTTP utiliza apenas a biblioteca padrão do Python, timeout de dez
segundos e parâmetros codificados. Testes substituem o transporte por respostas
determinísticas e nunca dependem da internet.

## Endpoints

- `GET /api/clima/previsoes/`;
- `GET /api/clima/previsoes/{id}/`;
- `POST /api/clima/previsoes/atualizar/`.

A listagem aceita `propriedade`, `data_inicio`, `data_fim` e `ordering`.

## Critérios de aceite

- [x] somente usuários autenticados consultam ou atualizam previsões;
- [x] propriedade sem coordenadas recebe mensagem clara;
- [x] falhas externas retornam erro tratado sem corromper dados;
- [x] atualização repetida não duplica propriedade e data;
- [x] temperatura, chuva, umidade e vento são armazenados;
- [x] alertas agrícolas são gerados por regras documentadas;
- [x] frontend permite escolher propriedade e atualizar previsão;
- [x] migrations, testes, build e documentação estão consistentes.

## Limitações

Previsões são estimativas do provedor e não substituem estação meteorológica
local. Os limites de alerta são operacionais e devem ser refinados futuramente
por cultura, fase fenológica e região.

## Validação

- testes do módulo climático: 11 aprovados;
- testes de componentes e geometria: 6 aprovados;
- build de produção do frontend: aprovado.
