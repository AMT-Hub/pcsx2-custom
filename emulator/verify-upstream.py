from pathlib import Path
import hashlib,json,sys
root=Path(sys.argv[1]);kit=Path(__file__).resolve().parent
for n,h in json.loads((kit/'nightly-upstream-sha256.json').read_text()).items():
 if hashlib.sha256((root/n).read_bytes().replace(b'\r\n',b'\n')).hexdigest()!=h:
  raise SystemExit('Unreviewed or modified nightly source: '+n)
print('All reviewed nightly integration files match.')
