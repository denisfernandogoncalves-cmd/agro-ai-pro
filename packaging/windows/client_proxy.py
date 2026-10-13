"""Interface local persistente; apenas a API depende do servidor compartilhado."""
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import mimetypes
from pathlib import Path
import threading
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlsplit
from urllib.request import build_opener, HTTPRedirectHandler, Request


class SemRedirecionamento(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class ServidorLocal(ThreadingHTTPServer):
    daemon_threads = True

    def close(self):
        self.shutdown()
        self.server_close()


class ClienteHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, resources, servidor, **kwargs):
        self.resources = resources
        self.servidor = servidor
        super().__init__(*args, **kwargs)

    def log_message(self, *_args):
        pass  # Não gravar URLs, conteúdo ou tokens do usuário no log.

    def responder(self, status, conteudo, tipo="application/json", headers=None):
        self.send_response(status)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(conteudo)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for nome, valor in (headers or {}).items():
            self.send_header(nome, valor)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(conteudo)

    def encaminhar(self):
        try:
            tamanho = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return self.responder(400, b'{"detail":"Tamanho invalido."}')
        if self.headers.get("Transfer-Encoding") or not 0 <= tamanho <= 11 * 1024 * 1024:
            return self.responder(413, b'{"detail":"Arquivo excede o limite."}')
        corpo = self.rfile.read(tamanho) if tamanho else None
        headers = {nome: self.headers[nome] for nome in (
            "Authorization", "Content-Type", "Accept", "Idempotency-Key", "Confirmar-Periodo-Fechado",
        ) if nome in self.headers}
        # A rota sempre permanece no servidor configurado, mesmo para //host e redirecionamentos.
        requisicao = Request(self.servidor + self.path, data=corpo, headers=headers, method=self.command)
        try:
            resposta = build_opener(SemRedirecionamento()).open(requisicao, timeout=15)
        except HTTPError as erro:
            resposta = erro
        except (URLError, TimeoutError, OSError):
            return self.responder(502, b'{"detail":"Servidor indisponivel. Use o painel de trabalho offline."}',
                                  headers={"X-Agro-Offline": "1"})
        with resposta:
            retorno = {nome: resposta.headers[nome] for nome in ("Content-Disposition",) if nome in resposta.headers}
            return self.responder(resposta.code, resposta.read(), resposta.headers.get("Content-Type", "application/json"), retorno)

    def atender(self):
        rota = urlsplit(self.path)
        if rota.scheme or rota.netloc or not self.path.startswith("/") or self.path.startswith("//"):
            return self.responder(400, b'{"detail":"Rota invalida."}')
        if rota.path.startswith(("/api/", "/media/")):
            return self.encaminhar()
        if self.command not in ("GET", "HEAD"):
            return self.responder(405, b'{"detail":"Metodo indisponivel."}')
        raiz = self.resources / ("static" if rota.path.startswith("/static/") else "frontend")
        recurso = rota.path[len("/static/"):] if rota.path.startswith("/static/") else rota.path.lstrip("/")
        alvo = (raiz / unquote(recurso)).resolve()
        if not alvo.is_relative_to(raiz.resolve()):
            return self.responder(404, b'{"detail":"Arquivo indisponivel."}')
        if not alvo.is_file():
            if Path(recurso).suffix or raiz.name == "static":
                return self.responder(404, b'{"detail":"Arquivo indisponivel."}')
            alvo = raiz / "index.html"
        tipo = mimetypes.guess_type(alvo)[0] or "application/octet-stream"
        return self.responder(200, alvo.read_bytes(), tipo)

    do_GET = do_HEAD = do_POST = do_PUT = do_PATCH = do_DELETE = atender


def start_client(resources, address, remote_port=18765, local_port=18765):
    ip = ipaddress.IPv4Address(address)
    partes = ip.packed
    if not (partes[0] == 10 or partes[0] == 172 and 16 <= partes[1] <= 31 or
            partes[0] == 192 and partes[1] == 168 or ip.is_loopback):
        raise ValueError("Use o IPv4 privado do servidor.")
    if str(ip) == "127.0.0.1" and remote_port == local_port:
        raise ValueError("O cliente local não pode encaminhar requisições para si mesmo.")
    handler = partial(ClienteHandler, resources=Path(resources).resolve(), servidor=f"http://{ip}:{remote_port}")
    server = ServidorLocal(("127.0.0.1", local_port), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
