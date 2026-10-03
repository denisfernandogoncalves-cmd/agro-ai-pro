"""Gera uma nova cópia privada e testa a restauração sem alterar o banco operacional."""
from pathlib import Path
import subprocess
import sys
from verificar_backup import verificar
root=Path(__file__).resolve().parent.parent
resultado=subprocess.run([sys.executable,str(root/"scripts/backup_local.py")],check=True,capture_output=True,text=True)
print(resultado.stdout,end="")
caminho=Path(resultado.stdout.splitlines()[0])
verificar(caminho)
