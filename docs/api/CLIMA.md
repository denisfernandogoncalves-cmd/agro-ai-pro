# API de clima

Todos os endpoints exigem autenticação JWT e respeitam o escopo de propriedades
da PR #16.

## Previsão diária

```http
GET /api/clima/previsoes/?propriedade=1&ordering=data
```

Filtros:

- `propriedade`: identificador exato;
- `data_inicio` e `data_fim`: datas ISO `AAAA-MM-DD`;
- `ordering`: data, temperaturas, chuva ou equivalentes com `-`.

Cada registro pode informar:

- temperatura e sensação mínima/máxima;
- chuva e probabilidade;
- umidade;
- vento, direção e rajadas;
- pressão, cobertura de nuvens e radiação;
- ponto de orvalho e evapotranspiração;
- nascer e pôr do sol;
- condição para pulverização e colheita;
- riscos de deriva, lavagem e estresse hídrico;
- alerta agrícola, fonte e atualização.

## Previsão horária

```http
GET /api/clima/horarias/?propriedade=1&ordering=data_hora
```

Filtros:

- `propriedade`;
- `data_inicio` e `data_fim` em ISO 8601;
- `ordering`: `data_hora`, `temperatura`, `precipitacao_mm` ou `vento_kmh`.

## Estado atual e agendamento

```http
GET /api/clima/previsoes/status/?propriedade=1
```

Resposta resumida:

```json
{
  "configuracao": {
    "status": "atualizado",
    "frequencia_minutos": 180,
    "ultima_atualizacao": "2026-07-27T09:00:00-03:00",
    "proxima_atualizacao": "2026-07-27T12:00:00-03:00",
    "desatualizado": false
  },
  "atual": {
    "temperatura": 24.5,
    "condicao": "Parcialmente nublado"
  },
  "proxima_hora": {},
  "alertas_ativos": 0
}
```

O objeto não expõe URL completa do provedor, chave, token ou credencial.

## Resumo por período

```http
GET /api/clima/previsoes/resumo/?propriedade=1&data_inicio=2026-07-01&data_fim=2026-07-31
```

Retorna acumulado de chuva e evapotranspiração, temperaturas mínima, máxima e
média, além da quantidade de alertas ativos.

## Atualização manual

```http
POST /api/clima/previsoes/atualizar/
Content-Type: application/json

{"propriedade": 1}
```

A resposta continua sendo a lista de previsões diárias, preservando o contrato da
versão anterior. A ação força uma atualização, mas mantém lock contra concorrência.

Papéis autorizados:

- administrador;
- gestor;
- operador;
- superusuário.

Usuários somente leitura não podem gerar chamadas ao provedor.

## Alertas internos

```http
GET /api/clima/alertas/?propriedade=1&ativo=true
```

```http
POST /api/clima/alertas/10/marcar_lido/
```

Marcar como lido altera apenas a notificação interna. Não envia e-mail, SMS,
WhatsApp ou push externo.

## Histórico de atualizações

```http
GET /api/clima/atualizacoes/?propriedade=1
```

Cada tentativa registra:

- início e término;
- sucesso, erro, cache ou atualização ignorada;
- origem das coordenadas;
- quantidade de chamadas ao provedor;
- quantidade de previsões diárias e horárias;
- tipo de erro e mensagem sanitizada.

## Configuração por propriedade

```http
GET /api/clima/configuracoes/?propriedade=1
```

```http
PATCH /api/clima/configuracoes/1/
Content-Type: application/json

{
  "frequencia_minutos": 180,
  "limite_chuva_forte_mm": "50.00",
  "limite_vento_forte_kmh": "40.00",
  "dias_sem_chuva_alerta": 7
}
```

Somente administrador, gestor e superusuário podem alterar frequência e limites.
Campos de execução, contadores, coordenadas usadas e dados atuais são somente
leitura.

## Atualização automática

O serviço local executa:

```bash
python manage.py atualizar_clima --continuous --interval-seconds 10800
```

No Docker Compose, o serviço é `clima-worker`.

A frequência padrão por propriedade é 180 minutos. Cache e lock usam Redis local
quando configurado, com fallback para cache em memória em testes.

## Coordenadas

A resolução usa, em ordem:

1. latitude e longitude da propriedade;
2. centro do GeoJSON da propriedade;
3. centro cadastrado de talhão;
4. centro do GeoJSON de talhão.

Sem localização válida, a API preserva os dados anteriores e retorna erro tratado.
Nenhuma coordenada é inventada a partir de município ou UF.

## Provedor, custo e licenciamento

O padrão é Open-Meteo, sem chave no código ou frontend. Nenhum serviço pago foi
ativado.

O endpoint público gratuito é limitado a uso não comercial. Para produção
comercial, configure uma instância auto-hospedada compatível ou obtenha autorização
expressa antes de avaliar plano comercial.

Documentação operacional completa:

- `docs/CLIMA-AUTOMATICO.md`.
