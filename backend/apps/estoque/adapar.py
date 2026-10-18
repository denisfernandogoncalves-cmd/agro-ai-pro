"""Consulta a publicação oficial vigente; não infere composição pelo nome."""
import io
import re
import unicodedata
from contextlib import closing
from threading import Lock
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

from django.core import signing
from django.core.cache import cache
from django.utils import timezone

PORTAL = "https://www.adapar.pr.gov.br/Pagina/Agrotoxicos-no-Parana"
SALT = "estoque.adapar"
_pdfium_lock = Lock()


class ConsultaIndisponivel(Exception):
    pass


def normalizar(texto):
    return " ".join(unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().upper().split())


class LinksLista(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.href = ""

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.href = dict(attrs).get("href", "")

    def handle_data(self, data):
        if "LISTA DE AGROTOXICOS APTOS" in normalizar(data):
            self.links.append(urljoin(PORTAL, self.href))

    def handle_endtag(self, tag):
        if tag == "a":
            self.href = ""


def baixar(url, limite):
    destino = urlsplit(url)
    if destino.scheme != "https" or destino.hostname != "www.adapar.pr.gov.br":
        raise ConsultaIndisponivel("Fonte oficial inválida.")
    with urlopen(Request(url, headers={"User-Agent": "AGRO-AI-PRO/1.0"}), timeout=15) as resposta:
        if urlsplit(resposta.url).hostname != destino.hostname:
            raise ConsultaIndisponivel("Redirecionamento da fonte não reconhecido.")
        dados = resposta.read(limite + 1)
    if len(dados) > limite:
        raise ConsultaIndisponivel("Publicação excede o limite de leitura.")
    return dados


def extrair(dados, nome, fonte):
    try:
        import pdfplumber
        import pypdfium2 as pdfium
    except ImportError as exc:
        raise ConsultaIndisponivel("Leitor da publicação ADAPAR indisponível. O cadastro manual de produtos continua disponível.") from exc
    resultados = []
    vistos = set()
    # Localiza as páginas por texto nativo; não mantém o layout pesado de todas
    # as páginas em memória para cada nome digitado.
    candidatas = []
    with _pdfium_lock, pdfium.PdfDocument(dados) as indice:
        if not len(indice) or len(indice) > 250:
            raise ConsultaIndisponivel("Formato da publicação não reconhecido.")
        for numero in range(len(indice)):
            with closing(indice[numero]) as pagina:
                with closing(pagina.get_textpage()) as texto:
                    conteudo = texto.get_text_bounded()
            if numero == 0:
                data = re.search(r"Atualização:\s*(\d{2}/\d{2}/\d{4})", conteudo)
                if not data or "INGREDIENTE ATIVO" not in conteudo:
                    raise ConsultaIndisponivel("Formato da publicação não reconhecido.")
            if nome in normalizar(conteudo):
                candidatas.append(numero)
    with pdfplumber.open(io.BytesIO(dados)) as documento:
        for numero in candidatas:
            pagina = documento.pages[numero]
            for tabela in pagina.extract_tables():
                for linha in tabela:
                    celulas = [" ".join(c.split()) for c in linha if c and c.strip()]
                    if len(celulas) != 7:
                        continue  # Restrições e linhas incompletas não são produtos.
                    comercial, empresa, classe, ativos, concentracao, registro, _ = celulas
                    if nome not in normalizar(comercial) or not registro.isdigit():
                        continue
                    chave = (comercial, registro)
                    if chave in vistos:
                        continue
                    vistos.add(chave)
                    resultados.append({"nome": comercial, "empresa": empresa,
                        "classe_agronomica": classe, "principios_ativos": ativos,
                        "concentracao": concentracao, "registro_mapa": registro,
                        "fonte_adapar": fonte, "atualizacao_fonte": data.group(1),
                        "consultado_em": timezone.now().isoformat()})
            pagina.close()
    return resultados


def consultar(nome):
    termo = normalizar(nome)
    try:
        publicacao = cache.get("adapar:publicacao:v1")
        if publicacao is None:
            parser = LinksLista()
            parser.feed(baixar(PORTAL, 2_000_000).decode("utf-8"))
            if not parser.links:
                raise ConsultaIndisponivel("Lista oficial não encontrada no portal.")
            fonte = parser.links[0]
            dados = baixar(fonte, 12_000_000)
            publicacao = (fonte, dados)
            cache.set("adapar:publicacao:v1", publicacao, 3600)
        fonte, dados = publicacao
        resultados = extrair(dados, termo, fonte)
        resultados.sort(key=lambda item: (normalizar(item["nome"]) != termo, item["nome"]))
        total = len(resultados)
        for item in resultados[:20]:
            item["consulta_adapar"] = signing.dumps(item, salt=SALT, compress=True)
        return {"resultados": resultados[:20], "total": total, "fonte": fonte}
    except ConsultaIndisponivel:
        raise
    except Exception as exc:
        raise ConsultaIndisponivel("Consulta ADAPAR indisponível. Tente novamente ou preencha manualmente.") from exc
