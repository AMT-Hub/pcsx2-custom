"""Build the accepted updater overlay, checking it against the tested archive."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument('--accepted-test-zip', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
repo = Path(__file__).resolve().parents[3]
if hashlib.sha256(args.accepted_test_zip.read_bytes()).hexdigest() != '7b01fbe3f777b9d8f5e5f6e399b715954441fee73a2f2620d14b471ff8fd85e3':
    raise SystemExit('Input is not the exact user-accepted test archive.')
prefix = 'custom-pcsx2/updater/'
files = {}
with zipfile.ZipFile(args.accepted_test_zip) as accepted:
    for name in ('Engine.ps1', 'Feed.ps1', 'Updater.ps1'):
        original = accepted.read('custom-pcsx2/updater-launcher-validation-test1/' + name)
        current = (repo / 'updater' / name).read_bytes()
        expected = original
        if name == 'Updater.ps1':
            old = b"$form.Text='PCSX2 Controlled Updater 0.3.0 - launcher validation test1'"
            new = b"$form.Text='PCSX2 Controlled Updater 0.3.0'"
            assert original.count(old) == 1
            expected = original.replace(old, new)
        assert current == expected, 'Untested change in ' + name
        files[prefix + name] = current
files[prefix + 'COPYING.GPLv3'] = (repo / 'COPYING.GPLv3').read_bytes()
files['README-Updater-0.3.0.txt'] = Path(__file__).with_name('README-Updater-0.3.0.txt').read_bytes()
manifest = {name: {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()} for name, data in files.items()}
files[prefix + 'UPDATER-0.3.0-FILES-SHA256.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
args.output.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(args.output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
    for name, data in sorted(files.items()):
        info = zipfile.ZipInfo(name, date_time=(2026, 10, 14, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        archive.writestr(info, data, compresslevel=9)
with zipfile.ZipFile(args.output) as archive:
    assert archive.testzip() is None
    assert set(archive.namelist()) == set(files)
    for name, data in files.items():
        assert archive.read(name) == data
print(json.dumps({'filename': args.output.name, 'bytes': args.output.stat().st_size,
                  'sha256': hashlib.sha256(args.output.read_bytes()).hexdigest(),
                  'files': manifest}, indent=2))
