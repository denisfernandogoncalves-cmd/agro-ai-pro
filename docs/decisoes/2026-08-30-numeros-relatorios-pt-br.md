# Números dos relatórios em pt-BR — 30/08/2026

## Pedido, causa e escopo

O usuário solicitou conferir novamente os cálculos e usar ponto para milhares
e vírgula para casas decimais. Na imagem de Produção por propriedade, kg já
estava formatado, enquanto hectares, sacas e médias eram exibidos diretamente
como strings decimais da API: `70.000`, `687.750`, `9.825`.

Branch `codex/remover-grupos-colheita`, worktree `runtime-origin-main`.
A alteração preserva os trabalhos anteriores e se limita à apresentação dos
relatórios, aos testes e à documentação.

## Conferência dos cálculos

Foi executada consulta somente leitura das três cargas ativas e suas oito
parcelas, usando Decimal e arredondamento para três casas. Foram conferidos:

- líquido = bruto × (1 − desconto percentual / 100);
- sacas totais = líquido / 60, arredondado;
- soma dos kg e das sacas das parcelas igual aos totais da carga;
- peso proporcional à área congelada, com tolerância de 0,001 kg para resíduo;
- média = sacas totais / área total congelada, arredondada.

Resultado: nenhuma divergência nesses critérios. A distribuição do resíduo de
arredondamento foi preservada para que as sacas das parcelas fechem com o total.
Não foram alteradas regras, snapshots, áreas, cargas ou posições de estoque.
A conferência não é uma auditoria completa do histórico de movimentações.

Exemplo da carga #41: 60.000 kg brutos, desconto de 1,750%, líquido de
58.950,000 kg e 982,500 sacas. Em 100 hectares, a média é 9,825 sc/ha.
Sagrilo tem 70,000 ha, 41.265,000 kg e 687,750 sc; teste 2 tem 30,000 ha,
17.685,000 kg e 294,750 sc.

## Implementação

`frontend/src/pages/Relatorios/RelatoriosPage.tsx` centraliza a formatação com
`Intl.NumberFormat("pt-BR")`. Kg, hectares, sacas, sementes e médias usam três
casas; contagens usam formato inteiro. Campos textuais como CAD/PRO e safra não
são convertidos. Dados ausentes ou inválidos mostram travessão.

`frontend/scripts/test-components.mjs` acrescenta três cenários de renderização:
valores da imagem, transporte acima de mil sacas e valores pequenos/negativos/
ausentes. A documentação da API foi atualizada em `docs/api/RELATORIOS.md`.
Não houve alteração de backend, models, migrations ou dependências.

## Validação

Na pasta `frontend`:

```powershell
npm.cmd test
npm.cmd run build
```

Resultado: 32 cenários de componentes/submissão/geometria/PWA e 13 cenários de
autenticação aprovados; TypeScript e build aprovados. Não há script `lint`.
Permanece o aviso de bundle acima de 500 kB.

Na pasta `backend`, com `DJANGO_SETTINGS_MODULE=config.settings.test`:

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test apps.graos.test_cargas_colhidas apps.relatorios.test_operacionais --noinput
```

Resultado: verificações aprovadas, sem mudança de esquema detectada, 32 testes
aprovados no SQLite. A suíte PostgreSQL completa da etapa anterior não foi
repetida para esta mudança de apresentação.

Na raiz do worktree:

```powershell
docker compose -p agro-ai-pro build frontend
$env:FRONTEND_PORT='5174'
docker compose -p agro-ai-pro up -d --no-deps frontend
git -c core.safecrlf=false diff --check
```

Build Docker e atualização local aprovados. A tela Produção por propriedade
foi conferida no navegador: as oito linhas usam vírgulas decimais em áreas,
sacas e médias e pontos de milhar nos pesos. O diff foi revisado sem erros de
espaços. Nenhum formulário de gravação foi enviado.

Sem commit, push, merge ou publicação em produção. O JSON mantém a representação
decimal canônica exigida pelas integrações; os separadores brasileiros são
exclusivos da apresentação.
