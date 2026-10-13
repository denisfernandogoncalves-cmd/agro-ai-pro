from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from client_proxy import start_client


class RemoteHandler(BaseHTTPRequestHandler):
    recusados = 0
    recebido = None

    def log_message(self, *_args):
        pass

    def do_GET(self):
        if self.path == "/api/redirecionar/":
            self.send_response(302)
            self.send_header("Location", "http://127.0.0.1:1/fora/")
            self.end_headers()
            return
        self.send_response(401)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"detail":"Login necessario."}')

    def do_POST(self):
        RemoteHandler.recebido = (self.headers.get("Authorization"), self.rfile.read(int(self.headers["Content-Length"])))
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok":true}')


class ClientProxyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "frontend").mkdir()
        (self.root / "frontend/index.html").write_text("<html>Interface local</html>")
        self.remote = ThreadingHTTPServer(("127.0.0.1", 0), RemoteHandler)
        threading.Thread(target=self.remote.serve_forever, daemon=True).start()
        self.client = start_client(self.root, "127.0.0.1", self.remote.server_port, 0)
        self.url = f"http://127.0.0.1:{self.client.server_port}"

    def tearDown(self):
        self.client.close()
        self.remote.shutdown()
        self.remote.server_close()
        self.tmp.cleanup()

    def test_interface_abre_sem_servidor_e_api_informa_indisponibilidade(self):
        self.remote.shutdown()
        self.remote.server_close()
        with urlopen(self.url + "/") as resposta:
            self.assertIn(b"Interface local", resposta.read())
        with self.assertRaises(HTTPError) as falha:
            urlopen(self.url + "/api/health/")
        self.assertEqual(falha.exception.code, 502)
        self.assertEqual(falha.exception.headers["X-Agro-Offline"], "1")

    def test_encaminha_corpo_e_token_sem_remover_autenticacao(self):
        body = b'{"observacoes":"Teste"}'
        pedido = Request(self.url + "/api/offline/cargas/", data=body,
                         headers={"Authorization": "Bearer token-ficticio"}, method="POST")
        with urlopen(pedido) as resposta:
            self.assertEqual(resposta.code, 200)
            self.assertEqual(resposta.headers["Cache-Control"], "no-store")
        self.assertEqual(RemoteHandler.recebido, ("Bearer token-ficticio", body))
        with self.assertRaises(HTTPError) as falha:
            urlopen(self.url + "/api/privado/")
        self.assertEqual(falha.exception.code, 401)

    def test_nao_serve_arquivo_fora_da_pasta_da_interface(self):
        (self.root / "segredo.txt").write_text("Nao expor")
        with self.assertRaises(HTTPError) as falha:
            urlopen(self.url + "/%2e%2e/segredo.txt")
        self.assertEqual(falha.exception.code, 404)

    def test_nao_segue_redirecionamento_da_api(self):
        with self.assertRaises(HTTPError) as falha:
            urlopen(self.url + "/api/redirecionar/")
        self.assertEqual(falha.exception.code, 302)

    def test_endereco_publico_e_loop_rejeitados(self):
        for endereco in ("8.8.8.8", "127.0.0.1"):
            with self.assertRaises(ValueError):
                start_client(self.root, endereco)


if __name__ == "__main__":
    unittest.main()
