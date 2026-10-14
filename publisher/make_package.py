"""Package an already-reviewed runtime. Signing is an explicit release approval."""
import argparse, base64, hashlib, io, json, pathlib, re, zipfile
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
p=argparse.ArgumentParser()
p.add_argument('--runtime',required=True,type=pathlib.Path)
p.add_argument('--root',required=True,type=pathlib.Path,help='Existing portable root for ShaderGlass dependency hashes')
p.add_argument('--key',required=True,type=pathlib.Path)
p.add_argument('--id',required=True)
p.add_argument('--label',required=True)
p.add_argument('--output',required=True,type=pathlib.Path)
p.add_argument('--approve-tested-release',action='store_true',required=True)
a=p.parse_args()
assert re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}',a.id) and a.id!='legacy'
key=serialization.load_pem_private_key(a.key.read_bytes(),password=None)
files={x.relative_to(a.runtime).as_posix():x.read_bytes() for x in sorted(a.runtime.rglob('*')) if x.is_file()}
assert files['portable.txt'].strip()==b'../../..'
for name in files:
 assert not name.startswith('.') and not any(x.lower() in ('bios','memcards','sstates','inis','gamesettings','inputprofiles') for x in name.split('/'))
requirements=['ShaderGlass/ShaderGlass-PCSX2.exe','ShaderGlass/Profiles/retro-crisis_1080p-curved_PS2.sgp']
m={'schema':1,'product':'CustomPCSX2','channel':'approved','data_schema':1,'id':a.id,'label':a.label,'features':['auto-bios','shaderglass','sorting-title'],'files':{n:{'size':len(b),'sha256':hashlib.sha256(b).hexdigest()} for n,b in files.items()},'requires':{n:hashlib.sha256((a.root/n).read_bytes()).hexdigest() for n in requirements}}
b=json.dumps(m,sort_keys=True,separators=(',',':')).encode()
sig=key.sign(b,padding.PKCS1v15(),hashes.SHA256())
output=io.BytesIO()
with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,6) as z:
 z.writestr('manifest.json',b);z.writestr('manifest.sig',sig)
 for n,data in files.items(): z.writestr('runtime/'+n,data)
a.output.write_bytes(output.getvalue())
with zipfile.ZipFile(a.output) as z:assert z.testzip() is None
print(a.output, a.output.stat().st_size, hashlib.sha256(a.output.read_bytes()).hexdigest())
