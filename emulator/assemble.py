"""Public runtime-only packaging: no BIOS images or personal installation input."""
from pathlib import Path
import hashlib,io,json,zipfile
NIGHTLY='pcsx2-v2.9.127-windows-x64-Qt.7z'
EXPECTED='d780d14e3951705c3a4f51d30e1e3c894ef40db4024f5bce36bf29740222554a'
TAG=NIGHTLY.removeprefix('pcsx2-').removesuffix('-windows-x64-Qt.7z')
VERSION=TAG.removeprefix('v')
RUNTIME_NAME=f'PCSX2-Nightly-{VERSION}-runtime-UNSIGNED.zip'
def check_inputs(root):
 p=root/NIGHTLY
 if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=EXPECTED:
  raise RuntimeError('Place the original official '+NIGHTLY+' beside Build.cmd; its SHA-256 must match the pinned archive.')
def package(root,stage,official):
 check_inputs(root)
 data={p.relative_to(stage).as_posix():p.read_bytes() for p in stage.rglob('*') if p.is_file()}
 data['portable.txt']=b'../../..\r\n'
 for n in ['auto-bios.enabled','bios-catalogue.tsv','bios-rules.tsv']:
  data['custom-pcsx2/'+n]=(root/'policy'/n).read_bytes()
 assert 'PCSX2-ShaderPrototype.exe' in data and 'resources/patches.zip' in data
 assert 'resources/automatic-sorting.ini' in data, 'Automatic sorting catalogue is required.'
 assert not any(n.split('/')[0].lower() in ['bios','memcards','sstates','inis','gamesettings','inputprofiles'] for n in data)
 output=io.BytesIO()
 with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,6) as z:
  for n,v in sorted(data.items()):z.writestr(n,v)
 target=root/RUNTIME_NAME;target.write_bytes(output.getvalue())
 with zipfile.ZipFile(target) as z:assert z.testzip() is None
 (root/'RUNTIME-SHA256.json').write_text(json.dumps({n:hashlib.sha256(v).hexdigest() for n,v in data.items()},indent=2))
 print('Built unsigned runtime for review:',target)
