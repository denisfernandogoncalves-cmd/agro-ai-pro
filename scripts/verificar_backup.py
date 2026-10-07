"""Valida hashes/ZIPs e restaura dump em PostgreSQL efêmero, sem rede ou volume persistente."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import time
import uuid
import zipfile
import tempfile


def restaurar_uploads(arquivo, destino, referencias):
    """Extrai somente para área isolada, validando os caminhos referidos pelo banco."""
    destino=destino.resolve()
    with zipfile.ZipFile(arquivo) as uploads:
        for item in uploads.infolist():
            alvo=(destino/item.filename).resolve()
            if not alvo.is_relative_to(destino) or ":" in item.filename or "\\" in item.filename or (item.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("Caminho inseguro no backup de uploads.")
        uploads.extractall(destino)
        arquivos=sum(not item.is_dir() for item in uploads.infolist())
    for referencia in referencias:
        alvo=(destino/referencia).resolve()
        if not alvo.is_relative_to(destino) or not alvo.is_file():
            raise ValueError("Upload referenciado pelo banco não foi recuperado.")
    return arquivos

ROOT=Path(__file__).resolve().parent.parent
LABEL="agro.backup.validation"

def run(args,**kwargs):
    return subprocess.run(args,check=True,**kwargs)

def verificar(dest):
    dest=dest.resolve()
    manifesto=json.loads((dest/"manifesto.json").read_text(encoding="utf-8"))
    for nome, esperado in manifesto["arquivos"].items():
        caminho=(dest/nome).resolve()
        if not caminho.is_relative_to(dest) or not caminho.is_file():
            raise ValueError("Arquivo inválido no manifesto.")
        with caminho.open("rb") as source:
            digest=hashlib.file_digest(source,"sha256").hexdigest()
        if caminho.stat().st_size!=esperado["bytes"] or digest!=esperado["sha256"]:
            raise ValueError(f"Integridade falhou: {nome}")
        if caminho.suffix==".zip":
            with zipfile.ZipFile(caminho) as archive:
                if archive.testzip() is not None: raise ValueError("ZIP corrompido.")
    dump=dest/"banco.dump"
    if "banco.dump" not in manifesto["arquivos"] or not dump.is_file():
        raise ValueError("O ensaio requer pg_dump custom; cópia física offline não pode ser restaurada por este script.")
    # Sem portas, rede, volumes de produção ou senha operacional. PGDATA está em tmpfs.
    nome="agro-backup-validacao-"+uuid.uuid4().hex[:16]
    criado=False
    try:
        run(["docker","run","-d","--name",nome,"--label",LABEL+"=1","--network","none","--tmpfs","/var/lib/postgresql/data:rw,size=2g","-e","POSTGRES_HOST_AUTH_METHOD=trust","postgres:17"],capture_output=True)
        criado=True
        for tentativa in range(60):
            ready=subprocess.run(["docker","exec",nome,"pg_isready","-U","postgres"],capture_output=True)
            if ready.returncode==0:break
            time.sleep(1)
        else:raise RuntimeError("PostgreSQL isolado não ficou pronto.")
        with dump.open("rb") as source:
            run(["docker","exec","-i",nome,"pg_restore","--exit-on-error","--no-owner","--no-privileges","-U","postgres","-d","postgres"],stdin=source,capture_output=True)
        resultado=run(["docker","exec",nome,"psql","-U","postgres","-d","postgres","-At","-c","SELECT count(*) FROM information_schema.tables WHERE table_schema='public'; SELECT count(*) FROM django_migrations;"],capture_output=True,text=True).stdout.splitlines()
        if len(resultado)!=2 or int(resultado[0])<10 or int(resultado[1])<1:raise RuntimeError("Restauração incompleta.")
        consulta="SELECT coalesce(json_agg(arquivo_kml),'[]'::json) FROM (SELECT arquivo_kml FROM propriedades_propriedade WHERE arquivo_kml IS NOT NULL AND arquivo_kml <> '' UNION SELECT arquivo_kml FROM talhoes_talhao WHERE arquivo_kml IS NOT NULL AND arquivo_kml <> '') arquivos;"
        referencias=json.loads(run(["docker","exec",nome,"psql","-U","postgres","-d","postgres","-At","-c",consulta],capture_output=True,text=True).stdout)
        if "uploads.zip" not in manifesto["arquivos"]:
            raise ValueError("Backup de uploads ausente do manifesto.")
        with tempfile.TemporaryDirectory(prefix="ensaio-uploads-",dir=dest) as area:
            recuperados=restaurar_uploads(dest/"uploads.zip",Path(area),referencias)
        prova={"data":datetime.datetime.now().astimezone().isoformat(),"backup":str(dest),"hashes":True,"zip_crc":True,"restauracao_isolada":True,"postgres":"17","rede":"none","volume":"tmpfs efêmero","tabelas":int(resultado[0]),"migrations":int(resultado[1])}
        prova.update(uploads_restaurados=recuperados, referencias_uploads_verificadas=len(referencias), recuperacao_conjunta=True)
        arquivo=dest/("verificacao-restauracao-"+datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")+".json")
        arquivo.write_text(json.dumps(prova,ensure_ascii=False,indent=2),encoding="utf-8")
        print("Restauração isolada aprovada:",arquivo)
        return prova
    finally:
        if criado:
            label=run(["docker","inspect",nome,"--format","{{ index .Config.Labels \"agro.backup.validation\" }}"],capture_output=True,text=True).stdout.strip()
            if label!="1" or not nome.startswith("agro-backup-validacao-"):raise RuntimeError("Limpeza bloqueada: contêiner não reconhecido.")
            run(["docker","rm","-f",nome],capture_output=True)

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backup",type=Path)
    args=parser.parse_args()
    verificar(args.backup)
