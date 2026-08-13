# Homologação gratuita — Cloudflare Pages + Koyeb

## Objetivo

Disponibilizar o AGRO-AI-PRO para homologação sem servidor próprio, sem gravar
credenciais no repositório e usando apenas modalidades gratuitas. Esta
arquitetura não é indicada para produção crítica.

## Arquitetura

- Cloudflare Pages publica o frontend React/Vite como conteúdo estático.
- Koyeb executa a API Django em uma instância Web Service `free`.
- Koyeb Database Service executa PostgreSQL 17 em uma instância `free`.
- Cloudflare R2 é opcional para preservar KML. Sem R2, a mídia local da
  instância gratuita é explicitamente descartável.

O frontend recebe a URL pública da API durante o build. A API permite somente
a origem HTTPS exata do frontend. Banco, chave Django e credenciais R2 são
Secrets do provedor e nunca fazem parte do Git.

## Limites conhecidos do custo zero

Condições consultadas em 13/08/2026:

- Koyeb permite uma instância Web Service gratuita com 512 MB de RAM, 0,1 vCPU
  e 2 GB de SSD efêmero. Ela reduz a zero após uma hora sem tráfego.
- O banco gratuito da Koyeb possui 1 GB e cinco horas mensais de computação
  ativa. Ele dorme após inatividade e pode adicionar atraso à primeira consulta.
- Cloudflare Pages permite 500 builds mensais no plano gratuito.
- R2 inclui mensalmente 10 GB de armazenamento Standard, um milhão de
  operações Classe A e dez milhões de operações Classe B. Ultrapassar a franquia
  pode gerar cobrança; por isso o R2 não é obrigatório nesta homologação.

Fontes oficiais:

- <https://www.koyeb.com/docs/reference/instances>
- <https://www.koyeb.com/docs/databases>
- <https://developers.cloudflare.com/pages/platform/limits/>
- <https://developers.cloudflare.com/r2/pricing/>

## 1. Preparar o PostgreSQL na Koyeb

1. Criar uma conta Koyeb e manter o plano sem custo. O provedor pode solicitar
   validação de conta ou meio de pagamento; isso não autoriza selecionar uma
   instância paga.
2. Em **Databases**, criar `agro-ai-pro-homologacao`.
3. Selecionar PostgreSQL 17, região Washington, D.C., e instância `free`.
4. Em **Connection Details**, copiar a connection string `postgres://...`.
5. Criar um Secret Koyeb chamado `agro-ai-pro-database-url` contendo essa
   connection string. Não colar o valor em arquivo, commit, issue ou PR.

## 2. Publicar a API na Koyeb

Criar um Web Service conectado ao repositório GitHub:

| Campo | Valor |
| --- | --- |
| Branch | `main` |
| Builder | Dockerfile |
| Dockerfile location | `Dockerfile.koyeb` |
| Instance | `free` |
| Region | Washington, D.C. |
| Port | `8000`, protocolo HTTP |
| Route | `/` |
| Health check | HTTP `GET /api/health/` |

Adicionar as variáveis públicas abaixo:

```text
DJANGO_SETTINGS_MODULE=config.settings.production
DJANGO_ALLOWED_HOSTS={{ KOYEB_PUBLIC_DOMAIN }}
DJANGO_CORS_ALLOWED_ORIGINS=https://SEU-PROJETO.pages.dev
DJANGO_CSRF_TRUSTED_ORIGINS=https://SEU-PROJETO.pages.dev
DJANGO_ALLOW_EPHEMERAL_MEDIA=true
PORT=8000
WEB_CONCURRENCY=1
GUNICORN_THREADS=2
```

Adicionar como Secrets:

| Variável do serviço | Fonte segura |
| --- | --- |
| `DATABASE_URL` | Secret `agro-ai-pro-database-url` |
| `DJANGO_SECRET_KEY` | Secret com valor aleatório exclusivo |

Uma chave pode ser gerada localmente sem compartilhá-la:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

O container aplica migrations com retentativas e inicia Gunicorn. A publicação
deve ser considerada saudável somente quando `GET /api/health/` responder 200.

## 3. Publicar o frontend no Cloudflare Pages

Em **Workers & Pages**, importar o mesmo repositório GitHub e configurar:

| Campo | Valor |
| --- | --- |
| Production branch | `main` |
| Root directory | `frontend` |
| Build command | `npm run build:cloudflare` |
| Build output directory | `dist` |
| Node.js | 22 |

Adicionar a variável de build:

```text
VITE_API_URL=https://SEU-SERVICO.koyeb.app/api
```

O build específico rejeita URL vazia, HTTP, localhost ou caminho sem `/api`.
Cloudflare Pages trata o projeto como SPA porque não existe `404.html` no topo.
O arquivo `public/_headers` acrescenta cabeçalhos defensivos e cache imutável
apenas aos assets versionados.

Depois de obter o domínio definitivo `pages.dev`, atualizar na Koyeb
`DJANGO_CORS_ALLOWED_ORIGINS` e `DJANGO_CSRF_TRUSTED_ORIGINS` com a origem exata
e solicitar novo deploy da API.

## 4. Persistência opcional de KML com R2

O disco da instância Koyeb gratuita é efêmero. Na homologação descartável,
`DJANGO_ALLOW_EPHEMERAL_MEDIA=true` confirma conscientemente essa limitação.

Para preservar KML:

1. Ativar R2 Standard somente após revisar os limites gratuitos e alertas de
   uso da conta Cloudflare.
2. Criar o bucket `agro-ai-pro-homologacao`.
3. Criar token **Object Read & Write** restrito somente a esse bucket.
4. Salvar Access Key ID e Secret Access Key como Secrets Koyeb.
5. Configurar no serviço:

```text
R2_ACCESS_KEY_ID=<Secret Koyeb>
R2_SECRET_ACCESS_KEY=<Secret Koyeb>
R2_BUCKET_NAME=agro-ai-pro-homologacao
R2_ENDPOINT_URL=https://SEU_ACCOUNT_ID.r2.cloudflarestorage.com
```

6. Remover `DJANGO_ALLOW_EPHEMERAL_MEDIA` e redeployar.

Configuração parcial do R2 interrompe o startup deliberadamente. Os objetos são
privados e o Django gera URLs assinadas quando necessário.

## 5. Validação após provisionamento

1. Abrir `https://SEU-SERVICO.koyeb.app/api/health/` e confirmar HTTP 200.
2. Abrir o domínio `pages.dev` e autenticar.
3. Verificar propriedades, talhões, cargas, grupos, produção/saldos, vendas e
   relatórios.
4. Recarregar uma rota do frontend diretamente para confirmar o fallback SPA.
5. No navegador, confirmar ausência de erros de CORS, conteúdo misto e console.
6. Reiniciar/redeployar a API. Se R2 estiver ativo, confirmar que um KML continua
   acessível. Sem R2, não usar dados que precisem ser preservados.
7. Conferir no painel dos dois provedores que somente modalidades `free` estão
   selecionadas e que o consumo continua dentro da franquia.

## Rollback

- Cloudflare Pages permite promover uma implantação anterior do frontend.
- Koyeb mantém deployments do serviço; selecionar o deployment anterior para a
  API.
- Migrations aditivas continuam no banco. Esta entrega de infraestrutura não
  cria migration nem altera dados.

## Segredos e responsabilidade operacional

- Nunca versionar `.env`, connection string, token R2 ou chave Django.
- Não reutilizar a chave de desenvolvimento.
- Restringir tokens ao recurso mínimo necessário.
- Homologação não substitui backup, monitoramento, disponibilidade ou suporte de
  uma produção real.
