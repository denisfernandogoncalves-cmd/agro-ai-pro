import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const read = (path) => readFile(new URL(path, import.meta.url), "utf8");
const [navigation, modules, page, api, css, app, main] = await Promise.all([
  read("../src/app/navigation.ts"),
  read("../src/app/ModuleRenderer.tsx"),
  read("../src/pages/Producao/ProducaoPage.tsx"),
  read("../src/api/producaoIntegrada.ts"),
  read("../src/pages/Producao/producao.css"),
  read("../src/AppEnterprise.tsx"),
  read("../src/main.tsx"),
]);

assert.match(navigation, /"producao"/);
assert.match(navigation, /label: "Produção"/);
assert.match(modules, /lazy\(\(\) => import\("\.\.\/pages\/Producao\/ProducaoPage"\)\)/);
assert.match(modules, /case "producao"/);
assert.match(page, /Gestão integrada/);
assert.match(page, /PermissionGuard allowed=\{canOperate/);
assert.match(page, /PermissionGuard allowed=\{canManage/);
assert.match(page, /Seu perfil não permite executar esta ação/);
assert.match(page, /status === 403/);
assert.match(page, /status === 404/);
assert.match(page, /Estoque só é atualizado após confirmação|estoque só é atualizado após confirmação/i);
assert.match(page, /Enviar e pré-validar/);
assert.match(page, /Confirmar importação/);
assert.match(page, /Exportar \{format\.toUpperCase\(\)\}/);
assert.match(api, /\/producao\/dashboard-integrado\//);
assert.match(api, /\/producao\/recebimentos\//);
assert.match(api, /\/producao\/saldos-graos\//);
assert.match(api, /\/producao\/contratos\//);
assert.match(api, /\/producao\/embarques\//);
assert.match(api, /\/producao\/importacoes\//);
assert.match(api, /responseType: "blob"/);
assert.match(css, /@media \(max-width: 720px\)/);
assert.match(css, /:root\[data-theme="dark"\]/);
assert.match(app, /item\.pode_editar/);
assert.match(app, /item\.pode_excluir/);
assert.match(app, /error\.response\?\.status === 403/);
assert.match(app, /error\.response\?\.status === 404/);
assert.match(main, /AppEnterprise/);

console.log("28 verificações da Gestão Integrada da Produção aprovadas.");
