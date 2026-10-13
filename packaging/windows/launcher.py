"""Aplicativo desktop de testes: PostgreSQL privado, Django e janela WebView2."""
import argparse
import ctypes
import ipaddress
import json
import logging
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
import tempfile
import urllib.request

PORT = int(os.environ.get("AGRO_TEST_PORT", "18765"))
DB_PORT = int(os.environ.get("AGRO_TEST_DB_PORT", "18766"))
ROOT = Path(os.environ.get("AGRO_PACKAGE_RESOURCES", str(Path(__file__).resolve().parents[2])))
DATA = Path(os.environ.get("AGRO_TEST_DATA", str(Path(os.environ["LOCALAPPDATA"]) / "AGRO-AI-PRO-Testes")))


def run_pg(command, *args, **kwargs):
    # Comandos pontuais precisam aguardar EOF dos filhos reexecutados pelo
    # PostgreSQL no Windows. pg_ctl inicia um servidor persistente: usar arquivo
    # de saída e aguardar o estado real, sem depender de handles herdados.
    with tempfile.TemporaryFile() as output:
        check = kwargs.pop("check", True)
        input_bytes = kwargs.pop("input", None)
        completion = None
        if command == "postgres" and "--single" in args and input_bytes is not None:
            cluster = Path(args[args.index("-D") + 1])
            completion = cluster.parent / (".pg-complete-" + secrets.token_hex(8) + ".tmp")
            sql_path = completion.as_posix().replace("'", "''")
            input_bytes = b"BEGIN;\n" + input_bytes + ("\nCOPY (SELECT 'ok') TO '" + sql_path + "';\nCOMMIT;\n").encode("utf-8")
        input_file = tempfile.TemporaryFile() if input_bytes is not None else None
        if input_file:
            input_file.write(input_bytes)
            input_file.seek(0)
        child_env = {k: v for k, v in os.environ.items()
                     if not k.startswith(("_PYI", "PYINSTALLER", "PYTHON")) and k != "PGDATA"}
        try:
            result = subprocess.run(
                [str(ROOT / "postgres" / "bin" / (command + ".exe")), *map(str, args)],
                creationflags=subprocess.CREATE_NO_WINDOW,
                stdin=input_file if input_file else subprocess.DEVNULL,
                stdout=output if command == "pg_ctl" else subprocess.PIPE, stderr=subprocess.STDOUT,
                env=child_env, cwd=ROOT / "postgres/bin", **kwargs,
            )
        finally:
            if input_file:
                input_file.close()
        if command == "pg_ctl":
            output.seek(0)
            result.stdout = output.read()
        if result.returncode and check:
            detail = "Falha na configuração de credenciais (conteúdo omitido)." if input_bytes and b"PASSWORD" in input_bytes else result.stdout.decode("utf-8", errors="replace")
            logging.error("PostgreSQL %s: %s", command, detail)
        if check:
            result.check_returncode()
        if completion:
            for _ in range(300):
                if completion.exists() and not (cluster / "postmaster.pid").exists():
                    completion.unlink()
                    break
                time.sleep(0.1)
            else:
                raise RuntimeError("O PostgreSQL não confirmou a conclusão da configuração offline.")
        if command == "pg_ctl" and args[-1] in ("start", "stop"):
            cluster = Path(args[args.index("-D") + 1])
            for _ in range(120):
                if args[-1] == "stop" and not (cluster / "postmaster.pid").exists():
                    break
                if args[-1] == "start" and (cluster / "postmaster.pid").exists():
                    ready = run_pg("pg_isready", "-h", "127.0.0.1", "-p", DB_PORT, check=False)
                    if ready.returncode == 0:
                        break
                time.sleep(0.25)
            else:
                raise RuntimeError("O PostgreSQL não confirmou a operação " + str(args[-1]))
        return result


def load_config():
    config_path = DATA / "config.json"
    if config_path.exists():
        return json.loads(config_path.read_text(encoding="utf-8"))
    from tkinter import Tk, messagebox, simpledialog
    ui = Tk()
    ui.withdraw()
    try:
        host = messagebox.askyesno("AGRO — testes", "Este computador vai armazenar os dados compartilhados?\n\nSim: manter os dados aqui.\nNão: conectar ao computador que mantém os dados.", parent=ui)
        if host:
            password = simpledialog.askstring("Primeiro acesso", "Crie uma senha de pelo menos 10 caracteres para o usuário admin:", show="*", parent=ui)
            if not password:
                raise SystemExit(0)
            if len(password) < 10:
                raise ValueError("A senha deve ter pelo menos 10 caracteres. Abra o AGRO novamente.")
            config = {"mode": "host", "secret": secrets.token_urlsafe(64), "db_password": secrets.token_urlsafe(40)}
            # A senha de acesso é usada uma vez e não é gravada no arquivo.
            config["initial_password"] = password
        else:
            address = simpledialog.askstring("Conectar ao AGRO", "Informe o IPv4 do computador que mantém os dados:", parent=ui)
            if not address:
                raise SystemExit(0)
            address = str(ipaddress.IPv4Address(address.strip()))
            if not ipaddress.ip_address(address).is_private:
                raise ValueError("Use um endereço da rede local.")
            config = {"mode": "client", "address": address}
        persisted = {k: v for k, v in config.items() if k != "initial_password"}
        config_path.write_text(json.dumps(persisted, indent=2), encoding="utf-8")
        return config
    finally:
        ui.destroy()


def setup_django(config):
    addresses = {"localhost", "127.0.0.1", socket.gethostname()}
    addresses.update(item[4][0] for item in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET))
    os.environ.update({
        "DJANGO_SETTINGS_MODULE": "config.settings.desktop",
        "AGRO_DESKTOP_SECRET": config["secret"],
        "AGRO_DESKTOP_DB_PASSWORD": config["db_password"],
        "AGRO_DESKTOP_DB_PORT": str(DB_PORT),
        "AGRO_DESKTOP_HOSTS": ",".join(sorted(addresses)),
        "AGRO_DESKTOP_DATA": str(DATA), "AGRO_DESKTOP_RESOURCES": str(ROOT),
        "AGRO_OFFLINE_ENABLE": "0" if config.get("offline_enabled") is False else "1",
    })
    sys.path.insert(0, str(ROOT / "backend"))
    import django
    django.setup()


def start_host(config):
    database = DATA / "database"
    if not (database / "PG_VERSION").exists():
        # O instalador inclui somente um cluster vazio, sem usuários com login.
        # Evita probes de initdb dentro de um aplicativo sem console no Windows.
        shutil.copytree(ROOT / "database-template", database)
    if not (DATA / "initialized").exists() and not (DATA / "database-activated").exists():
        password_sql = config["db_password"].replace("'", "''")
        run_pg("postgres", "--single", "-D", database, "postgres",
               input=("ALTER ROLE agro LOGIN PASSWORD '" + password_sql + "';\n").encode("utf-8"))
        (DATA / "database-activated").touch()
    run_pg("pg_ctl", "-D", database, "-l", DATA / "postgres.log", "-o",
           f"-p {DB_PORT} -h 127.0.0.1", "-w", "start")
    os.environ["PGPASSWORD"] = config["db_password"]
    try:
        exists = run_pg("psql", "-h", "127.0.0.1", "-p", DB_PORT, "-U", "agro", "-d", "postgres", "-tAc",
                        "SELECT 1 FROM pg_database WHERE datname='agro_testes'").stdout.strip()
        if not exists:
            run_pg("createdb", "-h", "127.0.0.1", "-p", DB_PORT, "-U", "agro", "agro_testes")
    finally:
        os.environ.pop("PGPASSWORD", None)
    setup_django(config)
    from django.core.management import call_command
    from django.contrib.auth import get_user_model
    # Preservar um dump íntegro antes de migrations em um banco já utilizado.
    if (DATA / "initialized").exists():
        backups = DATA / "backups"
        backups.mkdir(exist_ok=True)
        dump = backups / (time.strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(3) + ".dump")
        os.environ["PGPASSWORD"] = config["db_password"]
        try:
            run_pg("pg_dump", "-h", "127.0.0.1", "-p", DB_PORT, "-U", "agro", "-Fc", "-f", dump, "agro_testes")
            run_pg("pg_restore", "--list", dump)
            import hashlib
            dump.with_suffix(".sha256").write_text(hashlib.sha256(dump.read_bytes()).hexdigest(), encoding="ascii")
            import zipfile
            uploads = dump.with_suffix(".uploads.zip")
            with zipfile.ZipFile(uploads, "w", zipfile.ZIP_DEFLATED) as archive:
                for file in (DATA / "uploads").rglob("*"):
                    if file.is_file():
                        archive.write(file, file.relative_to(DATA / "uploads"))
            with zipfile.ZipFile(uploads) as archive:
                if archive.testzip() is not None:
                    raise RuntimeError("Falha ao verificar backup dos uploads.")
            uploads.with_suffix(".sha256").write_text(hashlib.sha256(uploads.read_bytes()).hexdigest(), encoding="ascii")
            config_backup = dump.with_suffix(".config.json")
            config_backup.write_text(json.dumps({k: v for k, v in config.items() if k != "initial_password"}), encoding="utf-8")
            config_backup.with_suffix(".sha256").write_text(hashlib.sha256(config_backup.read_bytes()).hexdigest(), encoding="ascii")
        finally:
            os.environ.pop("PGPASSWORD", None)
    call_command("migrate", interactive=False, verbosity=0)
    users = get_user_model()
    if not users.objects.filter(is_superuser=True).exists():
        password = config.pop("initial_password", None)
        if not password:
            from tkinter import Tk, simpledialog
            ui = Tk(); ui.withdraw()
            password = simpledialog.askstring("Primeiro acesso", "Crie a senha do usuário admin (mínimo 10 caracteres):", show="*", parent=ui)
            ui.destroy()
        if not password or len(password) < 10:
            raise ValueError("Uma senha com pelo menos 10 caracteres é necessária.")
        users.objects.create_superuser(username="admin", password=password)
    (DATA / "initialized").touch()
    from django.core.wsgi import get_wsgi_application
    from waitress.server import create_server
    server = create_server(get_wsgi_application(), host="0.0.0.0", port=PORT, threads=8)
    threading.Thread(target=server.run, daemon=True).start()
    return server


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke-test", action="store_true")
    parser.add_argument("--window-test", action="store_true")
    args = parser.parse_args()
    DATA.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=DATA / "app.log", level=logging.INFO, force=True)
    logging.info("Inicialização PID=%s argumentos=%s", os.getpid(), sys.argv)
    # Impedir duas instâncias do mesmo perfil e dois bancos na mesma porta.
    import msvcrt
    lock = (DATA / "instance.lock").open("a+b")
    lock.seek(0); lock.write(b"0"); lock.flush(); lock.seek(0)
    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
    server = None
    config = load_config()
    try:
        if config["mode"] == "host":
            server = start_host(config)
            address = "127.0.0.1"
        else:
            sys.path.insert(0, str(ROOT))
            from client_proxy import start_client
            server = start_client(ROOT, config["address"], remote_port=int(config.get("server_port", 18765)), local_port=PORT)
            address = "127.0.0.1"
        url = f"http://{address}:{PORT}"
        for attempt in range(60):
            try:
                with urllib.request.urlopen(url + "/api/health/", timeout=2) as response:
                    if json.load(response).get("service") != "backend":
                        raise ValueError("O endereço não respondeu como AGRO.")
                break
            except OSError:
                if config["mode"] == "client":
                    # A interface é local; o aparelho preparado pode abrir sem o servidor.
                    break
                if attempt == 59:
                    raise RuntimeError("Não foi possível conectar ao AGRO. Verifique se o computador dos dados está ligado e o aplicativo aberto.")
                time.sleep(0.5)
        if args.smoke_test:
            with urllib.request.urlopen(url, timeout=5) as response:
                assert b"<html" in response.read().lower()
            (DATA / "smoke-ok.txt").write_text("Banco, migrations, API e interface: OK", encoding="utf-8")
            return
        import webview
        webview.settings["ALLOW_DOWNLOADS"] = True
        webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = False
        window = webview.create_window("AGRO-AI-PRO — Testes", url, width=1360, height=850, min_size=(1024, 700), hidden=args.window_test)
        if args.window_test:
            def verify_window():
                try:
                    for _ in range(30):
                        if window.evaluate_js("document.querySelector('#root').children.length"):
                            (DATA / "window-ok.txt").write_text("Janela WebView2 e React: OK", encoding="utf-8")
                            break
                        time.sleep(0.5)
                finally:
                    window.destroy()
            window.events.loaded += verify_window
        webview.start(gui="edgechromium", private_mode=False, storage_path=str(DATA / "window"))
    finally:
        if server:
            server.close()
        if config["mode"] == "host" and (DATA / "database" / "postmaster.pid").exists():
            run_pg("pg_ctl", "-D", DATA / "database", "-m", "fast", "-w", "stop")
        lock.close()


if __name__ == "__main__":
    # Django e componentes .NET esperam streams válidos mesmo sem console.
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        logging.exception("Falha ao iniciar AGRO")
        if not any(flag in sys.argv for flag in ("--smoke-test", "--window-test")):
            ctypes.windll.user32.MessageBoxW(None, "Não foi possível iniciar o AGRO.\nConsulte app.log em " + str(DATA), "AGRO — testes", 0x10)
        sys.exit(1)
