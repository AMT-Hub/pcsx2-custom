"""Create an authenticated release feed from an already approved signed package."""
import argparse,base64,datetime as dt,hashlib,json,pathlib,zipfile
from urllib.parse import urlsplit
from cryptography.hazmat.primitives import serialization,hashes
from cryptography.hazmat.primitives.asymmetric import padding
p=argparse.ArgumentParser()
p.add_argument('--package',type=pathlib.Path,required=True)
p.add_argument('--url',required=True,help='Permanent HTTPS URL of this exact package asset')
p.add_argument('--key',type=pathlib.Path,required=True)
p.add_argument('--sequence',type=int,required=True,help='Strictly increasing feed revision, including refreshes')
p.add_argument('--days',type=int,default=30)
p.add_argument('--output',type=pathlib.Path,default=pathlib.Path('approved-feed.json'))
a=p.parse_args();u=urlsplit(a.url)
if u.scheme!='https' or not u.hostname or u.username or u.password or u.fragment:raise SystemExit('Use an HTTPS package URL without credentials or fragment.')
if not 1<=a.days<=90 or not 1<=a.sequence<=2147483647:raise SystemExit('Invalid sequence or expiry duration.')
key=serialization.load_pem_private_key(a.key.read_bytes(),password=None)
with zipfile.ZipFile(a.package) as z:
 b=z.read('manifest.json');key.public_key().verify(z.read('manifest.sig'),b,padding.PKCS1v15(),hashes.SHA256());m=json.loads(b)
 if m['product']!='CustomPCSX2' or m['channel']!='approved':raise SystemExit('Not an approved custom package')
 if z.testzip() is not None:raise SystemExit('Damaged ZIP')
feed={'schema':1,'product':'CustomPCSX2','channel':'approved','sequence':a.sequence,'expiresUtc':(dt.datetime.now(dt.timezone.utc)+dt.timedelta(days=a.days)).isoformat(),'release':{'id':m['id'],'label':m['label'],'url':a.url,'bytes':a.package.stat().st_size,'sha256':hashlib.sha256(a.package.read_bytes()).hexdigest()}}
b=json.dumps(feed,sort_keys=True,separators=(',',':')).encode()
sig=key.sign(b,padding.PKCS1v15(),hashes.SHA256())
a.output.write_text(json.dumps({'payload':base64.b64encode(b).decode(),'signature':base64.b64encode(sig).decode()},separators=(',',':'))+'\n')
print('Created',a.output,'sequence',a.sequence)
