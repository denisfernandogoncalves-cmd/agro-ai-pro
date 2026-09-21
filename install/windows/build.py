"""Build a Windows EXE with an allowlisted source snapshot; no local data."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(__file__).resolve().parent
OUTPUT = ROOT / 'install' / 'output' / datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
EXCLUDED = {'node_modules', '__pycache__', 'media', 'test-media', 'static', 'dist', '.venv'}


def entries():
    for name in ('backend', 'frontend', 'docker'):
        for folder, dirs, files in os.walk(ROOT / name):
            dirs[:] = [d for d in dirs if d not in EXCLUDED and not d.startswith('.')]
            for filename in sorted(files):
                path = Path(folder) / filename
                if filename.startswith('.') or path.suffix in ('.pyc', '.sqlite3', '.db', '.tsbuildinfo', '.log'):
                    continue
                yield path, path.relative_to(ROOT).as_posix()
    for name in ('.env.example', '.dockerignore'):
        yield ROOT / name, name
    yield SOURCE / 'compose.yaml', 'compose.yaml'
    for name in ('common.ps1', 'install.ps1', 'start.ps1'):
        yield SOURCE / name, 'desktop/' + name


def main():
    OUTPUT.mkdir(parents=True)
    manifest = {}
    payload = OUTPUT / 'payload.zip'
    with zipfile.ZipFile(payload, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path, target in entries():
            data = path.read_bytes()
            if target.endswith('.ps1'):
                # Windows PowerShell 5.1 requires BOM for Portuguese text.
                data = data.decode('utf-8-sig').encode('utf-8-sig')
            if target == 'docker/nginx/default.conf':
                data = data.replace(b'client_max_body_size 6m;', b'client_max_body_size 11m;')
            archive.writestr(target, data)
            manifest[target] = hashlib.sha256(data).hexdigest()
        archive.writestr('PACKAGE-MANIFEST.json', json.dumps(manifest, indent=2))
    with zipfile.ZipFile(payload) as archive:
        assert archive.testzip() is None
        assert '.env' not in archive.namelist()
    exe = OUTPUT / 'AGRO-AI-PRO-Teste-Setup.exe'
    compiler = Path(os.environ['WINDIR']) / 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    subprocess.run([str(compiler), '/nologo', '/target:exe', '/platform:anycpu',
                    '/reference:System.IO.Compression.dll',
                    '/resource:' + str(payload) + ',payload.zip',
                    '/out:' + str(exe), str(SOURCE / 'Installer.cs')], check=True)
    (OUTPUT / 'SHA256.txt').write_text(hashlib.sha256(exe.read_bytes()).hexdigest() + '  ' + exe.name + '\n')
    print(exe)
    print('Packaged files:', len(manifest))


if __name__ == '__main__':
    main()
