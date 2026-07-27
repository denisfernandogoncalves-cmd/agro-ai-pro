import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const read = (path) => readFile(new URL(path, import.meta.url), "utf8");
const [page, api, chart, css, modules] = await Promise.all([
  read("../src/pages/Mercado/MercadoPage.tsx"),
  read("../src/api/mercado.ts"),
  read("../src/pages/Mercado/GraficoMercado.tsx"),
  read("../src/pages/Mercado/mercado.css"),
  read("../src/app/ModuleRenderer.tsx"),
]);

for (const ativo of ["Soja CBOT", "Milho CBOT", "Trigo CBOT", "Farelo de soja", "Óleo de soja", "Petróleo Brent", "Dólar PTAX"]) {
  assert.match(page, new RegExp(ativo));
}
assert.match(page, /Cotação atual/);
assert.match(page, /Máxima/);
assert.match(page, /Mínima/);
assert.match(page, /Variação diária/);
assert.match(page, /Horário do dado/);
assert.match(page, /Intradiário/);
assert.match(page, /5 dias/);
assert.match(page, /30 dias/);
assert.match(page, /Análise automática integrada/);
assert.match(page, /Fatores de alta/);
assert.match(page, /Fatores de baixa/);
assert.match(page, /Clima no Corn Belt/);
assert.match(page, /atualizarMercadoEnterprise/);
assert.match(page, /Carregamento parcial/);
assert.match(page, /Histórico insuficiente/);
assert.match(api, /cotacoes-enterprise\/painel/);
assert.match(api, /cotacoes-enterprise\/serie/);
assert.match(api, /cotacoes-enterprise\/atualizar/);
assert.match(api, /soja_cbot/);
assert.match(api, /farelo_soja/);
assert.match(api, /oleo_soja/);
assert.match(chart, /market-chart__line/);
assert.match(chart, /role="img"/);
assert.match(css, /var\(--color-primary\)/);
assert.match(css, /:root|market-enterprise-page/);
assert.match(css, /@media \(max-width: 640px\)/);
assert.match(modules, /<MercadoPage selectedProperty=\{selectedProperty\}/);

console.log("32 verificações da interface Enterprise de Mercado aprovadas.");
