import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const read = (path) => readFile(new URL(path, import.meta.url), "utf8");
const [navigation, modules, page, api, css] = await Promise.all([
  read("../src/app/navigation.ts"),
  read("../src/app/ModuleRenderer.tsx"),
  read("../src/pages/LotesConjuntos/LotesConjuntosPage.tsx"),
  read("../src/api/lotesConjuntos.ts"),
  read("../src/pages/LotesConjuntos/lotes-conjuntos.css"),
]);

assert.match(navigation, /"lotes_conjuntos"/);
assert.match(navigation, /label: "Lotes conjuntos"/);
assert.match(modules, /lazy\(\(\) => import\("\.\.\/pages\/LotesConjuntos\/LotesConjuntosPage"\)\)/);
assert.match(modules, /case "lotes_conjuntos"/);
assert.match(page, /Lotes conjuntos de produção/);
assert.match(page, /Informações básicas/);
assert.match(page, /Seleção das propriedades|Seleção de propriedades/);
assert.match(page, /Áreas efetivamente colhidas/);
assert.match(page, /CAD\/PRO e talhões/);
assert.match(page, /Adicionar carga e viagem/);
assert.match(page, /Rateio opcional/);
assert.match(page, /Conferência e confirmação/);
assert.match(page, /buscar por nome|Buscar por nome/i);
assert.match(page, /Município/);
assert.match(page, /Produtor/);
assert.match(page, /CAD\/PRO/);
assert.match(page, /Propriedades selecionadas/);
assert.match(page, /Área efetivamente colhida/);
assert.match(page, /Produtividade conjunta/);
assert.match(page, /Conjunta sem rateio/);
assert.match(page, /Rateio automático pela área/);
assert.match(page, /Rateio manual/);
assert.match(page, /PermissionGuard/);
assert.match(page, /status === 403/);
assert.match(page, /status === 404/);
assert.match(page, /Exportar \{formato\.toUpperCase\(\)\}/);
assert.match(api, /\/producao\/lotes-conjuntos\//);
assert.match(api, /\/producao\/cargas-lotes-conjuntos\//);
assert.match(api, /\/producao\/saidas-lotes-conjuntos\//);
assert.match(api, /\/producao\/relatorios-lotes-conjuntos\//);
assert.match(api, /responseType: "blob"/);
assert.match(css, /@media \(max-width: 1100px\)/);
assert.match(css, /@media \(max-width: 680px\)/);
assert.match(css, /overflow-x: auto/);
assert.match(css, /grid-template-columns: 1fr/);

console.log("35 verificações da interface de Lotes Conjuntos aprovadas.");
