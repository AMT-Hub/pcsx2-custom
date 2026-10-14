"""Package the isolated updater test without modifying an existing installation."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument('--repair', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[3]
kit = Path(__file__).resolve().parent
if hashlib.sha256(args.repair.read_bytes()).hexdigest() != '69251ba788aacdd8ac0b26c6216115a97a4572141c7914310b4659ae816d4deb':
    raise SystemExit('Launcher repair is not the unchanged accepted ZIP')
prefix = 'custom-pcsx2/updater-launcher-validation-test1/'
files = {
    'Test-PCSX2-Update.cmd': kit / 'Test-PCSX2-Update.cmd',
    'README-Launcher-Validation-Test.txt': kit / 'README-Launcher-Validation-Test.txt',
    prefix + 'Start-Test.ps1': kit / 'Start-Test.ps1',
    prefix + 'PCSX2-Updater-Launcher-Repair-test1.zip': args.repair,
    prefix + 'COPYING.GPLv3': root / 'COPYING.GPLv3',
}
for name in ('Engine.ps1', 'Feed.ps1', 'Updater.ps1'):
    files[prefix + name] = root / 'updater' / name
for path in (root / 'launcher').iterdir():
    if path.is_file() and path.suffix not in ('.exe', '.o'):
        files[prefix + 'launcher-source/' + path.name] = path
files[prefix + 'tests/LauncherValidation.Tests.ps1'] = root / 'updater/tests/LauncherValidation.Tests.ps1'
manifest = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in files.items()}
args.output.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(args.output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
    for name, path in files.items():
        archive.write(path, name)
    archive.writestr(prefix + 'TEST-FILES-SHA256.json', json.dumps(manifest, indent=2) + '\n')
with zipfile.ZipFile(args.output) as archive:
    assert archive.testzip() is None
    for name, digest in manifest.items():
        assert hashlib.sha256(archive.read(name)).hexdigest() == digest, name
    assert not any(n in archive.namelist() for n in ('Custom-PCSX2.exe', 'PCSX2-Update.exe', 'pcsx2-qt.exe'))
    assert not any(n.startswith('custom-pcsx2/updater/') for n in archive.namelist())
print(json.dumps({'file': str(args.output.resolve()), 'bytes': args.output.stat().st_size,
                  'sha256': hashlib.sha256(args.output.read_bytes()).hexdigest(), 'files': len(manifest) + 1}))
