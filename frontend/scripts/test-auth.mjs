import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";


const codigo = await readFile(
  new URL("../src/api/propriedades.ts", import.meta.url),
  "utf8",
);

assert.match(codigo, /agro-ai-pro\.refresh-token/);
assert.match(codigo, /\/auth\/token\/refresh\//);
assert.match(codigo, /interceptors\.response\.use/);
assert.match(codigo, /requisicao\._retry = true/);
assert.match(codigo, /localStorage\.removeItem\(REFRESH_TOKEN_KEY\)/);

console.log("5 verificações de renovação da sessão aprovadas.");
