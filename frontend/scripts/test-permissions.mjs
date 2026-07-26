import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const read = (path) => readFile(new URL(path, import.meta.url), "utf8");
const [api, app, styles, shell, shared, security] = await Promise.all([
  read("../src/api/propriedades.ts"),
  read("../src/App.tsx"),
  read("../src/styles.css"),
  read("../src/components/layout/AppShell.tsx"),
  read("../src/components/shared/ui.tsx"),
  read("../../docs/SEGURANCA-MULTIUSUARIO.md"),
]);

assert.match(api, /papel_usuario: PapelPropriedade \| null/);
assert.match(api, /pode_editar: boolean/);
assert.match(api, /pode_excluir: boolean/);
assert.match(api, /pode_operar: boolean/);
assert.match(api, /\/propriedades\/permissoes\//);
assert.match(api, /dataset\.podeGerenciar/);
assert.match(api, /dataset\.podeOperar/);
assert.match(app, /item\.pode_editar/);
assert.match(app, /item\.pode_excluir/);
assert.match(app, /status === 403/);
assert.match(app, /status === 404/);
assert.match(app, /PermissionGuard/);
assert.match(styles, /data-pode-gerenciar="false"/);
assert.match(styles, /data-pode-operar="false"/);
assert.match(styles, /modulo-clima \.clima-controles button/);
assert.match(shell, /requiresProperty/);
assert.match(shell, /roleLabel/);
assert.match(shared, /allowed \? <>{children}<\//);
assert.match(security, /Administrador/);
assert.match(security, /Gestor/);
assert.match(security, /Operador/);
assert.match(security, /Somente leitura/);
assert.match(security, /HTTP 404/);
assert.match(security, /HTTP 403/);

console.log("24 verificações de preservação das permissões aprovadas.");
