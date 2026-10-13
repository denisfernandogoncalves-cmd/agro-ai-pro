"""Validar o binário entregue e a janela, mantendo dados de QA isolados."""
from pathlib import Path
import json
import os
import secrets
import subprocess
import sys

sys.stdout.reconfigure(errors="replace")

root = Path(__file__).resolve().parents[2]
data = root / ".packaging" / ("frozen-qa-" + secrets.token_hex(4))
data.mkdir()
config = {"mode": "host", "secret": secrets.token_urlsafe(64),
          "db_password": secrets.token_urlsafe(40), "initial_password": secrets.token_urlsafe(18)}
(data / "config.json").write_text(json.dumps(config), encoding="utf-8")
env = dict(os.environ, AGRO_TEST_DATA=str(data))
exe = root / "dist-windows/AGRO-AI-PRO-Standalone/AGRO-AI-PRO.exe"
for flag, marker in (("--smoke-test", "smoke-ok.txt"), ("--window-test", "window-ok.txt")):
    result = subprocess.run([str(exe), flag], env=env, timeout=120)
    if result.returncode != 0 or not (data / marker).exists():
        log = data / "app.log"
        if log.exists():
            print(log.read_text(encoding="utf-8", errors="replace")[-6000:])
        raise SystemExit("Falha na validação " + flag + ": " + str(data))
    print((data / marker).read_text(encoding="utf-8"))
    if (data / "database/postmaster.pid").exists():
        raise SystemExit("O banco não encerrou corretamente: " + str(data))
if "ERROR:" in (data / "app.log").read_text(encoding="utf-8", errors="replace"):
    raise SystemExit("O pacote registrou erro na inicialização: " + str(data))
config.pop("initial_password")
(data / "config.json").write_text(json.dumps(config), encoding="utf-8")
print("Evidências: " + str(data))
