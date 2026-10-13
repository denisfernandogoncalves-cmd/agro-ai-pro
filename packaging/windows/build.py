"""Construir o instalador com Python isolado incluído, sem instalação global."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
import secrets
import importlib.util

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / ".packaging"
SOURCE = Path(os.environ.get("AGRO_PACKAGE_SOURCE", str(ROOT / ".worktrees/runtime-origin-main")))
STAGE = WORK / "resources-runtime"
OUTPUT = ROOT / "dist-windows/AGRO-AI-PRO-Standalone"
FRONTEND = Path(os.environ.get("AGRO_PACKAGE_FRONTEND", str(WORK / "frontend-offline-dist")))


def copy_file(source, target):
    target = Path(target)
    if target.exists():
        left, right = Path(source).stat(), target.stat()
        if left.st_size == right.st_size and left.st_mtime_ns == right.st_mtime_ns:
            return str(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    return shutil.copy2(source, target)


if not (SOURCE / "backend/manage.py").is_file():
    raise SystemExit("Defina AGRO_PACKAGE_SOURCE para um checkout completo e validado.")
if not (FRONTEND / "index.html").is_file():
    raise SystemExit("Compile a interface com packaging/windows/prepare_frontend.py antes de montar o pacote.")
STAGE.mkdir(parents=True, exist_ok=True)
for folder in ("apps", "config"):
    for source in (SOURCE / "backend" / folder).rglob("*"):
        if source.is_file() and source.suffix in (".py", ".json") and "__pycache__" not in source.parts:
            copy_file(source, STAGE / "backend" / source.relative_to(SOURCE / "backend"))
copy_file(SOURCE / "backend/manage.py", STAGE / "backend/manage.py")
# Remover o prefixo visual dos números também nos downloads PDF/Excel.
for arquivo, substituicoes in {
    "apps/graos/romaneios_cargas.py": [('f"#{c.pk}"', 'f"{c.pk}"'), ('ROMANEIO DE ENTRADA #{pk}', 'ROMANEIO DE ENTRADA {pk}')],
    "apps/graos/romaneios_terceiros.py": [('f"#{entrada.pk}"', 'f"{entrada.pk}"'), ('ENTRADA DE TERCEIROS #{entrada.pk}', 'ENTRADA DE TERCEIROS {entrada.pk}')],
    "apps/vendas/romaneios.py": [('ROMANEIO DE SAÍDA #{saida.pk}', 'ROMANEIO DE SAÍDA {saida.pk}')],
}.items():
    destino = STAGE / "backend" / arquivo
    conteudo = (SOURCE / "backend" / arquivo).read_text(encoding="utf-8")
    for antigo, novo in substituicoes:
        if antigo not in conteudo and novo not in conteudo:
            raise RuntimeError(f"Confira a numeração do romaneio em {arquivo} antes de montar.")
        conteudo = conteudo.replace(antigo, novo)
    destino.write_text(conteudo, encoding="utf-8")
for source in (ROOT / "backend/apps/offline").rglob("*.py"):
    if "__pycache__" not in source.parts:
        copy_file(source, STAGE / "backend/apps/offline" / source.relative_to(ROOT / "backend/apps/offline"))
for overlay in ("config/settings/desktop.py", "config/desktop_urls.py"):
    copy_file(ROOT / "backend" / overlay, STAGE / "backend" / overlay)
copy_file(ROOT / "packaging/windows/launcher.py", STAGE / "desktop_runtime.py")
copy_file(ROOT / "packaging/windows/client_proxy.py", STAGE / "client_proxy.py")
if (SOURCE / "backend/templates").exists():
    shutil.copytree(SOURCE / "backend/templates", STAGE / "backend/templates", dirs_exist_ok=True, copy_function=copy_file)
shutil.copytree(FRONTEND, STAGE / "frontend", dirs_exist_ok=True, copy_function=copy_file)
shutil.copytree(WORK / "postgres/pgsql", STAGE / "postgres", dirs_exist_ok=True, copy_function=copy_file,
                ignore=shutil.ignore_patterns("pgAdmin 4", "StackBuilder", "doc", "include", "symbols"))
template = STAGE / "database-template"
if not (template / "ready.txt").exists():
    spec = importlib.util.spec_from_file_location("desktop_builder", ROOT / "packaging/windows/launcher.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = STAGE
    password_file = WORK / ("template-password-" + secrets.token_hex(4) + ".tmp")
    try:
        password_file.write_text(secrets.token_urlsafe(40), encoding="ascii")
        module.run_pg("initdb", "-D", template, "-U", "agro", "--pwfile", password_file,
                      "--auth=scram-sha-256", "--encoding=UTF8", "--locale=C")
        module.run_pg("postgres", "--single", "-D", template, "postgres",
                      input=b"ALTER ROLE agro NOLOGIN PASSWORD NULL;\n")
        (template / "ready.txt").write_text("Cluster vazio, role agro sem login e sem senha. PostgreSQL 17 x64.\n", encoding="utf-8")
    finally:
        password_file.unlink(missing_ok=True)
spec = importlib.util.spec_from_file_location("template_checker", ROOT / "packaging/windows/launcher.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.ROOT = STAGE
result = module.run_pg("postgres", "--single", "-D", template, "postgres",
                       input=b"SELECT count(*) AS unexpected FROM pg_authid WHERE rolcanlogin OR rolpassword IS NOT NULL;\n")
if b'unexpected = "0"' not in result.stdout:
    raise SystemExit("Banco-modelo não passou na validação de ausência de credenciais.")
if (template / "postmaster.pid").exists():
    raise SystemExit("Banco-modelo ainda está em uso. Nenhum pacote será gerado.")
sys.path.insert(0, str(STAGE / "backend"))
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.base"
import django
django.setup()
from django.conf import settings
from django.core.management import call_command
settings.STATIC_ROOT = STAGE / "static"
call_command("collectstatic", interactive=False, verbosity=0)
if "--stage-only" in sys.argv:
    print(STAGE)
    raise SystemExit(0)

shutil.copytree(STAGE, OUTPUT, dirs_exist_ok=True, copy_function=copy_file,
                ignore=shutil.ignore_patterns("__pycache__"))
runtime = OUTPUT / "runtime"
runtime.mkdir(exist_ok=True)
python_source = Path(sys.base_prefix)
for filename in ("pythonw.exe", "python.exe", "python3.dll", "python314.dll", "vcruntime140.dll", "vcruntime140_1.dll", "LICENSE.txt"):
    copy_file(python_source / filename, runtime / filename)
for folder in ("DLLs", "tcl"):
    shutil.copytree(python_source / folder, runtime / folder, dirs_exist_ok=True, copy_function=copy_file,
                    ignore=shutil.ignore_patterns("__pycache__"))
with zipfile.ZipFile(runtime / "python314.zip", "w", zipfile.ZIP_DEFLATED) as archive:
    for file in (python_source / "Lib").rglob("*.py"):
        relative = file.relative_to(python_source / "Lib")
        if not any(part in ("site-packages", "test", "tests", "__pycache__", "idlelib", "turtledemo") for part in relative.parts):
            archive.write(file, relative.as_posix())
shutil.copytree(Path(sys.prefix) / "Lib/site-packages", runtime / "Lib/site-packages", dirs_exist_ok=True,
                copy_function=copy_file, ignore=shutil.ignore_patterns("__pycache__", "PyInstaller", "pip", "pytest", "_pytest", "_pyinstaller_hooks_contrib"))
(runtime / "python314._pth").write_text("python314.zip\nDLLs\nLib/site-packages\n.\nimport site\n", encoding="ascii")
compiler = Path(os.environ.get("WINDIR", "C:/Windows")) / "Microsoft.NET/Framework64/v4.0.30319/csc.exe"
subprocess.run([str(compiler), "/nologo", "/target:winexe", "/platform:x64", "/reference:System.Windows.Forms.dll",
                "/out:" + str(OUTPUT / "AGRO-AI-PRO.exe"), str(ROOT / "packaging/windows/Launcher.cs")], check=True)
hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (WORK / "downloads").iterdir() if p.is_file()}
(ROOT / "dist-windows/componentes-sha256.json").write_text(json.dumps(hashes, indent=2), encoding="utf-8")
print("Pacote construído: " + str(OUTPUT))
