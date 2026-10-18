import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { createHash } from "node:crypto";
import { readFileSync, readdirSync } from "node:fs";
import { fileURLToPath } from "node:url";

const raiz = fileURLToPath(new URL(".", import.meta.url));
const hash = createHash("sha256");
function identificar(pasta: string) {
  for (const item of readdirSync(raiz + pasta, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
    const caminho = `${pasta}/${item.name}`;
    if (item.isDirectory()) identificar(caminho);
    else if (item.isFile()) hash.update(caminho).update("\0").update(readFileSync(raiz + caminho)).update("\0");
  }
}
identificar("src");
identificar("public");
for (const arquivo of ["package.json", "package-lock.json", "vite.config.ts"]) hash.update(arquivo).update(readFileSync(raiz + arquivo));
const versao = { versao: "2026.10.15.1", canal: "Web local", interface: hash.digest("hex").slice(0, 12), compiladoEm: new Date().toISOString() };


export default defineConfig({
  define: { __APP_BUILD__: JSON.stringify(versao) },
  plugins: [react(), tailwindcss(), {
    name: "identificacao-versao",
    generateBundle() { this.emitFile({ type: "asset", fileName: "versao.json", source: JSON.stringify(versao) }); },
  }],
});
