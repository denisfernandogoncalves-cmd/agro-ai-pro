import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

const navigation = await readFile(new URL("../src/app/navigation.ts", import.meta.url), "utf8");
const renderer = await readFile(new URL("../src/app/ModuleRenderer.tsx", import.meta.url), "utf8");
const app = await readFile(new URL("../src/App.tsx", import.meta.url), "utf8");
const api = await readFile(new URL("../src/api/producaoIntegrada.ts", import.meta.url), "utf8");
const imports = await readFile(new URL("../src/pages/Producao/ImportacaoHistory.tsx", import.meta.url), "utf8");
const styles = await readFile(new URL("../src/styles/production.css", import.meta.url), "utf8");
const access = await readFile(new URL("../../backend/apps/producao/grain_access.py", import.meta.url), "utf8");

assert.match(navigation, /"producao"/);
assert.match(navigation, /label: "Produção"/);
assert.match(renderer, /lazy\(\(\) => import\("\.\.\/pages\/Producao\/ProducaoIntegratedPage"\)\)/);
assert.match(renderer, /canManage/);
assert.match(renderer, /canOperate/);
assert.match(app, /<AppShell/);
assert.match(app, /item\.pode_editar/);
assert.match(app, /item\.pode_excluir/);
assert.match(app, /status === 403/);
assert.match(app, /status === 404/);
assert.match(api, /dashboard-integrado/);
assert.match(api, /relatorios-integrados/);
assert.match(api, /confirmarRecebimento/);
assert.match(api, /confirmarEmbarque/);
assert.match(api, /enviarImportacao/);
assert.match(api, /importacoes: importacoes\.data/);
assert.match(imports, /Confirmar importação/);
assert.match(imports, /Pré-visualização/);
assert.match(imports, /Inconsistências encontradas/);
assert.match(styles, /production-workspace/);
assert.match(styles, /import-review-layout/);
assert.match(styles, /@media \(max-width: 860px\)/);
assert.match(access, /PAPEL_ADMINISTRADOR/);
assert.match(access, /AcessoCadPro/);

const server = await createServer({
  appType: "custom",
  configLoader: "runner",
  logLevel: "silent",
  server: { middlewareMode: true },
});

try {
  const { default: ProducaoPage } = await server.ssrLoadModule(
    "/src/pages/Producao/ProducaoPage.tsx",
  );
  const html = renderToStaticMarkup(
    React.createElement(ProducaoPage, {
      properties: [],
      selectedProperty: null,
      shellSafra: "",
      canManage: false,
      canOperate: false,
    }),
  );
  assert.match(html, /Consolidando produção, estoque e comercialização/);
} finally {
  await server.close();
}

console.log("Testes de Produção, navegação, importação e permissões aprovados.");
