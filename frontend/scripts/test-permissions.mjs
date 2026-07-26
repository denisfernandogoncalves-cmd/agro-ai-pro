import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";


const api = await readFile(
  new URL("../src/api/propriedades.ts", import.meta.url),
  "utf8",
);
const app = await readFile(
  new URL("../src/App.tsx", import.meta.url),
  "utf8",
);
const estilos = await readFile(
  new URL("../src/styles.css", import.meta.url),
  "utf8",
);

assert.match(api, /papel_usuario: PapelPropriedade \| null/);
assert.match(api, /pode_editar: boolean/);
assert.match(api, /\/propriedades\/permissoes\//);
assert.match(api, /dataset\.podeGerenciar/);
assert.match(api, /dataset\.podeOperar/);
assert.match(app, /item\.pode_editar/);
assert.match(app, /item\.pode_excluir/);
assert.match(app, /status === 403/);
assert.match(estilos, /data-pode-gerenciar="false"/);
assert.match(estilos, /data-pode-operar="false"/);
assert.match(estilos, /modulo-clima \.clima-controles button/);

console.log("11 verificações de permissões da interface aprovadas.");
