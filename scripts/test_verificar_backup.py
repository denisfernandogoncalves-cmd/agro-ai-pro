import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from verificar_backup import verificar

class VerificacaoBackupTests(unittest.TestCase):
    def manifesto(self, root, arquivos):
        (root / "manifesto.json").write_text(json.dumps({"arquivos":arquivos}),encoding="utf-8")
    @patch("verificar_backup.run")
    def test_hash_divergente_impede_docker(self, run):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/"banco.dump").write_bytes(b"alterado")
            self.manifesto(root,{"banco.dump":{"bytes":8,"sha256":"0"*64}})
            with self.assertRaisesRegex(ValueError,"Integridade falhou"):verificar(root)
            run.assert_not_called()
    @patch("verificar_backup.run")
    def test_caminho_fora_da_copia_impede_docker(self, run):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);self.manifesto(root,{"../outro.dump":{"bytes":0,"sha256":"0"*64}})
            with self.assertRaisesRegex(ValueError,"Arquivo inválido"):verificar(root)
            run.assert_not_called()
    @patch("verificar_backup.run")
    def test_dump_fora_do_manifesto_nao_e_restaurado(self, run):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/"banco.dump").write_bytes(b"dump")
            self.manifesto(root,{})
            with self.assertRaisesRegex(ValueError,"pg_dump custom"):verificar(root)
            run.assert_not_called()

if __name__=="__main__":unittest.main()
