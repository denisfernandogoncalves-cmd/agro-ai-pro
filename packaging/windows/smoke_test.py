"""Validação de integração em banco novo, sem usar o ambiente do usuário."""
import importlib.util
import json
import os
from pathlib import Path
import secrets
import sys
import urllib.error
import urllib.request

root = Path(__file__).resolve().parents[2]
data = root / ".packaging" / ("qa-" + secrets.token_hex(4))
data.mkdir()
os.environ["AGRO_TEST_DATA"] = str(data)
spec = importlib.util.spec_from_file_location("agro_desktop", root / "packaging/windows/launcher.py")
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)
launcher.ROOT = root / ".packaging/resources-runtime"
password = secrets.token_urlsafe(18)
config = {"mode": "host", "secret": secrets.token_urlsafe(64),
          "db_password": secrets.token_urlsafe(40), "initial_password": password}
launcher.DATA.mkdir(exist_ok=True)


def request(path, body=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request("http://127.0.0.1:18765" + path,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers=headers)
    return urllib.request.urlopen(req, timeout=15)


server = None
try:
    server = launcher.start_host(config)
    from django.core.management import call_command
    call_command("check")
    call_command("makemigrations", check=True, dry_run=True, verbosity=0)
    with request("/api/auth/token/", {"username": "admin", "password": password}) as response:
        tokens = json.load(response)
    with request("/api/propriedades/", {"nome": "Teste instalador", "proprietario": "QA", "municipio": "Teste", "uf": "PR", "area_hectares": "10.00"}, tokens["access"]) as response:
        property_id = json.load(response)["id"]
    with request(f"/api/propriedades/{property_id}/", token=tokens["access"]) as response:
        assert json.load(response)["nome"] == "Teste instalador"
    with request("/api/auth/token/refresh/", {"refresh": tokens["refresh"]}) as response:
        assert json.load(response)["access"]
    try:
        request("/api/propriedades/")
        raise AssertionError("API sem autenticação")
    except urllib.error.HTTPError as error:
        assert error.code == 401
    with request("/") as response:
        assert b"<html" in response.read().lower()
    server.close(); server = None
    from django.db import connections
    connections.close_all()
    launcher.run_pg("pg_ctl", "-D", data / "database", "-m", "fast", "-w", "stop")
    server = launcher.start_host(config)
    with request(f"/api/propriedades/{property_id}/", token=tokens["access"]) as response:
        assert json.load(response)["id"] == property_id
    assert list((data / "backups").glob("*.dump"))
    print("OK: check, migrations, login, renovação JWT, proteção API, CRUD, reinício, persistência e backup.")
    print("Evidências isoladas: " + str(data))
finally:
    if server:
        server.close()
    if (data / "database" / "postmaster.pid").exists():
        launcher.run_pg("pg_ctl", "-D", data / "database", "-m", "fast", "-w", "stop")
