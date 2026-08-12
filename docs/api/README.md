# API do AGRO-AI-PRO

Documentação funcional: [Grupos de Colheita e Cargas Colhidas](CARGAS_COLHIDAS.md).

## Autenticação

Crie um usuário administrativo com `python manage.py createsuperuser` e obtenha
um token:

```http
POST /api/auth/token/
Content-Type: application/json

{"username": "usuario", "password": "senha"}
```

Envie o access token nas chamadas protegidas:

```http
Authorization: Bearer <access_token>
```

O token pode ser renovado em `POST /api/auth/token/refresh/`. A renovação
retorna um novo `access` e um novo `refresh`; o refresh apresentado fica
bloqueado e não pode ser reutilizado.

### Logout

```http
POST /api/auth/logout/
Content-Type: application/json

{"refresh": "<refresh_token_ficticio_e_truncado...>"}
```

O logout não exige access token. Ele revoga somente o refresh apresentado e é
idempotente:

- `204 No Content`: refresh revogado, já revogado ou expirado validado;
- `400 Bad Request`: campo ausente, token malformado, assinatura inválida ou
  tipo de token incorreto.

Login, refresh e logout retornam `Cache-Control: no-store, private`. Respostas
das APIs privadas também incluem `Vary: Authorization`.

A blacklist não invalida access tokens emitidos anteriormente. A janela
residual máxima é de 15 minutos. O cliente deve impedir novas renovações
durante o logout, remover access e refresh localmente, descartar dados privados
em memória e não armazenar tokens no service worker ou no Cache Storage.

Em falha de rede, o logout local pode ser concluído, mas a revogação remota não
deve ser considerada confirmada. O PWA mantém apenas o shell público em cache.

O schema e as interfaces interativas estão disponíveis em:

- `GET /api/schema.json`;
- `GET /api/swagger/`;
- `GET /api/redoc/`.

### Limpeza da blacklist

O comando oficial do Simple JWT 5.5.1 deve ser executado diariamente:

```powershell
python manage.py flushexpiredtokens
```

No ambiente Compose:

```powershell
docker compose exec -T backend sh -c "cd /app/backend && python manage.py flushexpiredtokens"
```

O repositório não possui Celery Beat ou outro agendador operacional. O deploy
deve configurar esse comando no cron, Windows Task Scheduler ou agendador já
adotado pelo ambiente. Não é necessário introduzir Celery para essa manutenção.

### Backup e rollback

Antes das migrations oficiais, deve ser criado e validado um backup do
PostgreSQL pelo processo normal da infraestrutura. O rollback preferencial é
restaurar a configuração anterior e manter as tabelas oficiais sem uso.
Executar `migrate token_blacklist zero` removeria o histórico da blacklist e
somente pode ser considerado após novo backup e autorização destrutiva
específica.

## Propriedades

O endpoint `/api/propriedades/` oferece CRUD, busca textual e ordenação. Campos:

- `nome`, `municipio` e `area_hectares`: obrigatórios;
- `proprietario`, `uf` e `observacoes`: opcionais;
- `latitude` e `longitude`: opcionais, mas devem ser enviados em conjunto;
- `arquivo_kml`: polígono `.kml` opcional, com limite de 5 MB.

Quando um KML é enviado, o backend valida o XML e o polígono e substitui as
coordenadas pelo centroide calculado. A resposta também inclui GeoJSON, área
geodésica aproximada e a diferença para a área declarada. Uma propriedade
vinculada a talhões não pode ser excluída; nesse caso, a API responde HTTP 409.

Consulte os exemplos e critérios completos em
[`docs/sprints/SPRINT-01.md`](../sprints/SPRINT-01.md).

## Talhões

A documentação dos endpoints, histórico agronômico, filtros, paginação,
validações de área, processamento KML e limitações geoespaciais está em
[Talhões](TALHOES.md).

## Clima

O módulo oferece previsão de sete dias por propriedade, histórico local,
temperatura, chuva, umidade, vento e alertas agrícolas. Consulte os endpoints e
limites em [Clima](CLIMA.md).

## Mercado

O módulo de Mercado mantém o histórico mensal de soja, milho, trigo e Brent,
resume variações, acompanha cinco regiões do Corn Belt e permite cadastrar
notícias com fonte HTTPS. Consulte [Mercado](MERCADO.md).

## Financeiro

O módulo Financeiro oferece cadastros auxiliares, contas a pagar e receber,
liquidação, filtros e resumo de fluxo de caixa. Consulte
[Financeiro](FINANCEIRO.md).

## Estoque

O módulo controla produtos, locais, lotes, entradas, saídas, validade, estoque
mínimo e rastreabilidade. Consulte [Estoque](ESTOQUE.md).

## Grãos

O módulo de Grãos controla armazéns, lotes, entradas, saídas, transferências,
capacidade, saldo físico e idempotência para integrações futuras. Consulte
[Grãos](GRAOS.md).

## Importações

O módulo de Importações gera um preview auditável de planilhas XLSX, com
normalização, erros, advertências, prevenção de duplicidade e associação
preliminar com Grãos, sem criar movimentações ou alterar saldos. Consulte
[Importações](IMPORTACOES.md).

## Operações

O módulo planeja, inicia, conclui e cancela operações por talhão, com custos e
baixa transacional dos insumos utilizados. Consulte [Operações](OPERACOES.md).

## Máquinas

O módulo controla frota, horímetro, uso em operações, abastecimentos e
manutenções. Consulte [Máquinas](MAQUINAS.md).

## Relatórios

O dashboard consolida indicadores gerenciais de todos os módulos. Consulte
[Relatórios](RELATORIOS.md).

## Assistente

Insights gerenciais explicáveis estão documentados em [IA](IA.md).
