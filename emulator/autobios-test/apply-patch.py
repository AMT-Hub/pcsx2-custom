"""Apply to a separate checkout matching upstream-sha256.json. Never edits an installation."""
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys

kit = pathlib.Path(__file__).resolve().parent
if len(sys.argv) != 2:
    raise SystemExit('Usage: python apply-patch.py PATH_TO_PCSX2_SOURCE')
root = pathlib.Path(sys.argv[1]).resolve()
expected = json.loads((kit / 'upstream-sha256.json').read_text())
for name, digest in expected.items():
    path = root / name
    # Git may check out CRLF on Windows. Normalise only for source verification.
    data = path.read_bytes().replace(b'\r\n', b'\n')
    if hashlib.sha256(data).hexdigest() != digest:
        raise SystemExit(f'Wrong or edited upstream file: {name}. Use the clean, reviewed checkout named in build.py.')
for path in (kit / 'patch').rglob('*.h'):
    dst = root / path.relative_to(kit / 'patch')
    if dst.exists():
        raise SystemExit(f'Refusing to overwrite {dst}')
subprocess.run(['git', '-C', str(root), 'apply', '--check', str(kit / 'auto-bios.patch')], check=True)
subprocess.run(['git', '-C', str(root), 'apply', str(kit / 'auto-bios.patch')], check=True)
for path in (kit / 'patch').rglob('*.h'):
    dst = root / path.relative_to(kit / 'patch')
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, dst)
print('Applied experimental compatibility Auto BIOS source change. A full PCSX2 build is still required.')
