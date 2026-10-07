import json
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from django.test import SimpleTestCase
from django.utils import timezone
from .backup_status import situacao_backup


class SituacaoBackupTests(SimpleTestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.raiz = Path(self.temp.name)
        self.agora = timezone.now()

    def fixture(self, instante):
        pasta = self.raiz / "agro-ai-pro-teste"
        pasta.mkdir(exist_ok=True)
        arquivos = {}
        for nome in ("banco.dump", "codigo-atual.zip", "uploads.zip"):
            (pasta/nome).write_bytes(b"teste")
            arquivos[nome] = {"bytes": 5}
        (pasta/"manifesto.json").write_text(json.dumps({"data": instante.isoformat(), "arquivos": arquivos}), encoding="utf-8")
        (pasta/"verificacao-restauracao-teste.json").write_text(json.dumps({"data": instante.isoformat(), "hashes": True, "zip_crc": True, "restauracao_isolada": True}), encoding="utf-8")
        return pasta

    def test_ausente_incompleto_em_dia_e_atrasado(self):
        self.assertEqual(situacao_backup(self.raiz, self.agora)["situacao"], "ausente")
        pasta = self.fixture(self.agora-timedelta(days=1))
        resultado = situacao_backup(self.raiz, self.agora)
        self.assertEqual(resultado["situacao"], "em_dia")
        self.assertNotIn(str(self.raiz), json.dumps(resultado))
        self.assertEqual(situacao_backup(self.raiz, self.agora+timedelta(days=7))["situacao"], "atrasado")
        (pasta/"uploads.zip").write_bytes(b"incompleto")
        self.assertEqual(situacao_backup(self.raiz, self.agora)["situacao"], "ausente")

    def test_prova_invalida_ou_futura_nao_aprova_backup(self):
        pasta = self.fixture(self.agora+timedelta(days=1))
        self.assertEqual(situacao_backup(self.raiz, self.agora)["situacao"], "ausente")

    def test_revalidar_copia_antiga_nao_renova_sua_idade(self):
        pasta = self.fixture(self.agora-timedelta(days=10))
        arquivo = pasta/"verificacao-restauracao-teste.json"
        prova = json.loads(arquivo.read_text(encoding="utf-8"))
        prova["data"] = self.agora.isoformat()
        arquivo.write_text(json.dumps(prova), encoding="utf-8")
        self.assertEqual(situacao_backup(self.raiz, self.agora)["situacao"], "atrasado")
        (pasta/"verificacao-restauracao-teste.json").write_text("json inválido", encoding="utf-8")
        self.assertEqual(situacao_backup(self.raiz, self.agora)["situacao"], "ausente")
