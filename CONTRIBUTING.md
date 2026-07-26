# Guia de contribuição

## Princípios

- preservar regras de negócio e compatibilidade existentes;
- realizar alterações pequenas, revisáveis e cobertas por evidências;
- manter código, testes, migrations e documentação consistentes;
- nunca incluir segredos, credenciais ou dados reais no repositório;
- não ocultar testes com falha nem reduzir segurança para fazê-los passar.

## Fluxo Git

1. atualizar a branch `main` por fast-forward;
2. criar uma branch curta a partir de `main`, por exemplo `fix/`, `feature/`,
   `docs/`, `test/`, `codex/` ou `chatgpt/`;
3. implementar e validar somente o escopo da tarefa;
4. revisar o diff e registrar riscos ou limitações;
5. criar Pull Request para `main`;
6. realizar merge apenas após revisão e CI aprovada.

Não faça force push na `main`, não reescreva migrations já publicadas e não
misture refatorações não relacionadas na mesma entrega.

## Backend

Antes de solicitar revisão, execute conforme o ambiente disponível:

```bash
cd backend
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Quando configurados, execute também lint, cobertura, auditoria de dependências e
`python manage.py check --deploy` com settings de produção válidos.

Regras transacionais relevantes devem ficar em serviços de domínio, não em
views ou serializers. Novas migrations precisam ser determinísticas e ter
estratégia segura para dados existentes.

## Frontend

```bash
cd frontend
npm ci
npm test
npm run build
```

TypeScript deve permanecer estrito. Chamadas HTTP devem passar pelo cliente de
API central e os estados de carregamento, vazio e erro precisam ser tratados.

## Docker e documentação

Valide `docker compose config` e, quando possível, o build e os healthchecks.
Atualize `README.md`, `ARCHITECTURE.md`, `ROADMAP.md`, requisitos, documentação
de API e changelog quando a alteração afetar esses contratos.

## Definição de pronto

Uma alteração está pronta quando:

- os critérios de aceite estão claros;
- testes aplicáveis foram executados e registrados;
- migrations e contratos de API foram verificados;
- não há segredo ou arquivo temporário no diff;
- documentação e changelog foram atualizados quando necessário;
- riscos remanescentes estão explícitos na Pull Request.
