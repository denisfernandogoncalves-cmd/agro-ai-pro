"""Compila a fonte funcional preservada com os ajustes do EXE e do trabalho offline."""
from pathlib import Path
import os
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(os.environ.get("AGRO_PACKAGE_SOURCE", ROOT / ".worktrees/runtime-origin-main"))
WORK = ROOT / ".packaging/frontend-offline"
OUTPUT = ROOT / ".packaging/frontend-offline-dist"


def preparar():
    frontend = SOURCE / "frontend"
    shutil.copytree(frontend, WORK, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("node_modules", "dist", "*.tsbuildinfo"))
    if not (WORK / "node_modules").exists():
        shutil.copytree(frontend / "node_modules", WORK / "node_modules",
                        ignore=shutil.ignore_patterns(".vite", ".vite-temp"))
    shutil.copytree(ROOT / "frontend/src/offline", WORK / "src/offline", dirs_exist_ok=True)
    shutil.copy2(ROOT / "packaging/windows/overlays/ComprovanteLancamento.tsx",
                 WORK / "src/components/ComprovanteLancamento.tsx")
    # Ajuste apenas de apresentação na cópia de montagem; IDs permanecem iguais.
    for arquivo, substituicoes in {
        "pages/CargasColhidas/CargasColhidasPage.tsx": [('Romaneio de entrada #${item.id}', 'Romaneio de entrada ${item.id}'), ('["Romaneio",`#${item.id}`]', '["Romaneio",`${item.id}`]')],
        "pages/CargasColhidas/romaneioTerceiro.ts": [('Romaneio de entrada de terceiros #${i.id}', 'Romaneio de entrada de terceiros ${i.id}'), ('["Romaneio",`#${i.id}`]', '["Romaneio",`${i.id}`]')],
        "pages/CargasColhidas/ListaRomaneiosEntrada.tsx": [('#{i.id}', '{i.id}'), ('#${i.id}', '${i.id}')],
        "pages/CargasColhidas/ExtratoTerceiro.tsx": [('Romaneio #{m.entrada}', 'Romaneio {m.entrada}')],
        "pages/Vendas/RomaneioVenda.tsx": [('Romaneio de saída #${saida.id}', 'Romaneio de saída ${saida.id}')],
        "pages/Vendas/LocalizadorRomaneios.tsx": [('Romaneio #${saida.id}', 'Romaneio ${saida.id}'), ('#{saida.id}', '{saida.id}'), ('Imprimir #${saida.id}', 'Imprimir ${saida.id}')],
    }.items():
        destino = WORK / "src" / arquivo
        conteudo = destino.read_text(encoding="utf-8")
        for antigo, novo in substituicoes:
            if antigo not in conteudo and novo not in conteudo:
                raise RuntimeError(f"Confira a numeração do romaneio em {arquivo} antes de montar.")
            conteudo = conteudo.replace(antigo, novo)
        destino.write_text(conteudo, encoding="utf-8")
    app = WORK / "src/App.tsx"
    texto = app.read_text(encoding="utf-8")
    inicio = texto.index("<AplicativoStatus />")
    fim = texto.index("</header>", inicio) + len("</header>")
    texto = texto[:fim] + "\n      <TrabalhoOffline />" + texto[fim:]
    app.write_text('import TrabalhoOffline from "./offline/TrabalhoOffline";\n' + texto, encoding="utf-8")
    api = WORK / "src/api/propriedades.ts"
    texto = api.read_text(encoding="utf-8")
    antigo = "!logoutExplicitoAtivo()\n        && obterGeracaoSessao() === generation"
    novo = "axios.isAxiosError(erroRenovacao)\n        && erroRenovacao.response?.status === 401\n        && !logoutExplicitoAtivo()\n        && obterGeracaoSessao() === generation"
    if texto.count(antigo) != 1:
        raise RuntimeError("Confira o tratamento de renovação antes de atualizar o pacote.")
    api.write_text(texto.replace(antigo, novo), encoding="utf-8")
    sw = WORK / "public/sw.js"
    texto = sw.read_text(encoding="utf-8")
    texto = texto.replace('`${CACHE_PREFIX}v2`', '`${CACHE_PREFIX}v3`')
    texto = texto.replace('url.pathname.startsWith("/api/")',
        '["/api/", "/media/", "/static/", "/admin/"].some(prefixo => url.pathname.startsWith(prefixo))')
    sw.write_text(texto, encoding="utf-8")
    node = shutil.which("node")
    if not node:
        raise RuntimeError("Node não encontrado para compilar a interface.")
    env = dict(os.environ, VITE_API_URL="/api")
    subprocess.run([node, "node_modules/typescript/bin/tsc", "--noEmit", "-p", "tsconfig.json"], cwd=WORK, env=env, check=True)
    subprocess.run([node, "node_modules/vite/bin/vite.js", "--configLoader", "runner", "build", "--outDir", str(OUTPUT)], cwd=WORK, env=env, check=True)
    print("Interface offline compilada: " + str(OUTPUT))


if __name__ == "__main__":
    preparar()
