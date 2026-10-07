import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import patch
from verificar_backup import verificar, restaurar_uploads

class VerificacaoBackupTests(unittest.TestCase):
    def test_uploads_recuperados_e_referencia_ausente(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);arquivo=root/'uploads.zip';destino=root/'isolado';destino.mkdir()
            with zipfile.ZipFile(arquivo,'w') as z:z.writestr('kml/campo.kml','<kml/>')
            self.assertEqual(restaurar_uploads(arquivo,destino,['kml/campo.kml']),1)
            self.assertEqual((destino/'kml/campo.kml').read_text(),'<kml/>')
            with self.assertRaisesRegex(ValueError,'não foi recuperado'):restaurar_uploads(arquivo,destino,['ausente.kml'])

    def test_uploads_nao_escapam_da_area_isolada(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);arquivo=root/'uploads.zip';destino=root/'isolado';destino.mkdir()
            with zipfile.ZipFile(arquivo,'w') as z:z.writestr('../fora.txt','inseguro')
            with self.assertRaisesRegex(ValueError,'inseguro'):restaurar_uploads(arquivo,destino,[])
            self.assertFalse((root/'fora.txt').exists())
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
