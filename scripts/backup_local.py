import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
import zipfile

root = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser(description='Backup verificado de código, uploads e PostgreSQL local, sem restauração.')
parser.add_argument('--destino', type=Path, default=root / 'backups')
args = parser.parse_args()
base = args.destino.resolve()
if base.is_relative_to(root) and base != (root / 'backups').resolve():
    raise SystemExit('Dentro do projeto, use somente a pasta backups para evitar incluir o backup em si mesmo.')
base.mkdir(parents=True, exist_ok=True)
dest = base / ('agro-ai-pro-' + datetime.datetime.now().strftime('%Y-%m-%d-%H%M%S-%f'))
dest.mkdir()
def run(args, **kwargs):
    return subprocess.run(args, check=True, cwd=root, **kwargs)

if dest.is_relative_to(root):
    run(['git', 'check-ignore', str(dest / 'banco-fisico.tar.gz')], capture_output=True)
state = json.loads(run(['docker', 'inspect', 'agro-ai-pro-postgres-1', '--format', '{{json .State}}'], capture_output=True, text=True).stdout)
if state['Running']:
    with (dest / 'banco.dump').open('wb') as out:
        run(['docker', 'exec', 'agro-ai-pro-postgres-1', 'sh', '-c', 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc'], stdout=out)
    with (dest / 'banco.dump').open('rb') as source, (dest / 'catalogo-banco.txt').open('wb') as out:
        run(['docker', 'exec', '-i', 'agro-ai-pro-postgres-1', 'pg_restore', '--list'], stdin=source, stdout=out)
    with (dest / 'banco.dump').open('rb') as source:
        run(['docker', 'exec', '-i', 'agro-ai-pro-postgres-1', 'pg_restore', '--file=/dev/null'], stdin=source)
    database_type = 'pg_dump custom; PostgreSQL 17; leitura integral pg_restore sem restauracao'
    count = 1
else:
    with (dest / 'banco-fisico.tar.gz').open('wb') as out:
        run(['docker', 'run', '--rm', '--network', 'none', '--volumes-from', 'agro-ai-pro-postgres-1:ro', 'postgres:17', 'tar', 'czf', '-', '-C', '/var/lib/postgresql/data', '.'], stdout=out)
    with tarfile.open(dest / 'banco-fisico.tar.gz') as archive:
        count = 0
        for member in archive:
            if member.isfile():
                f = archive.extractfile(member)
                while f.read(1024 * 1024):
                    pass
                count += 1
        assert count > 0
    database_type = 'copia fisica PostgreSQL 17 parado; volume somente leitura'
excluded = {'.git', 'backups', 'node_modules', '.venv', '__pycache__', 'dist', '.worktrees', 'media', 'test-media'}
with zipfile.ZipFile(dest / 'codigo-atual.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
    for folder, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in excluded]
        for name in files:
            file = Path(folder) / name
            archive.write(file, file.relative_to(root))
with zipfile.ZipFile(dest / 'uploads.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
    for file in (root / 'backend' / 'media').rglob('*'):
        if file.is_file():
            archive.write(file, file.relative_to(root / 'backend' / 'media'))
for name in ('codigo-atual.zip', 'uploads.zip'):
    with zipfile.ZipFile(dest / name) as archive:
        assert archive.testzip() is None
for name, args in [('estado-git.txt', ['git', 'status', '--short', '--branch', '--untracked-files=all']), ('alteracoes.patch', ['git', 'diff', '--binary'])]:
    with (dest / name).open('wb') as out:
        run(args, stdout=out)
manifest = {'data': datetime.datetime.now().isoformat(), 'checkout': str(root), 'tipo_banco': database_type, 'verificacao': 'banco leitura integral; ZIP CRC; SHA256', 'restauracao': False, 'arquivos': {}}
for file in dest.iterdir():
    manifest['arquivos'][file.name] = {'bytes': file.stat().st_size, 'sha256': hashlib.file_digest(file.open('rb'), 'sha256').hexdigest()}
(dest / 'manifesto.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
print(dest)
print('Backup validado:', len(manifest['arquivos']), 'arquivos; banco:', count, 'entradas')
