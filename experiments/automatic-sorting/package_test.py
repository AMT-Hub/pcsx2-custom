"""Test overlays only: no approved feed or release changes."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('channel', choices=['stable','nightly'])
    parser.add_argument('kit', type=Path)
    args=parser.parse_args()
    stage=args.kit/'work/package'
    # The accepted launcher's signed-runtime path requires an updater-installed
    # release. Exercise its existing manual/legacy path in a disposable copy;
    # never fabricate a release manifest or an approval for an unsigned build.
    runtime='custom-pcsx2/shader-prototype/'
    if args.channel=='stable':
        selected=['PCSX2-ShaderPrototype.exe','resources/automatic-sorting.ini','BUILD-INFO.json']
        files={runtime+n:(stage/n).read_bytes() for n in selected}
    else:
        files={runtime+p.relative_to(stage).as_posix():p.read_bytes() for p in stage.rglob('*') if p.is_file()}
        files[runtime+'portable.txt']=b'../..\r\n'
        # Keep accepted runtime BIOS rules with this experimental runtime.
        for name in ['auto-bios.enabled','bios-catalogue.tsv','bios-rules.tsv']:
            files[runtime+'custom-pcsx2/'+name]=(args.kit/'policy'/name).read_bytes()
    files['AUTOMATIC-SORTING-TEST-README.md']=(ROOT/'README.md').read_bytes()
    files['AUTOMATIC-SORTING-TEST-HASHES.json']=(json.dumps({n:hashlib.sha256(v).hexdigest() for n,v in files.items()},indent=2)+'\n').encode()
    output=args.kit/f'PCSX2-Automatic-Sorting-{args.channel}-0.1.0-test1-overlay.zip'
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,6) as z:
        for name,data in sorted(files.items()):z.writestr(name,data)
    with zipfile.ZipFile(output) as z:
        if z.testzip():raise ValueError('ZIP integrity check failed')
    print(output,hashlib.sha256(output.read_bytes()).hexdigest())


if __name__=='__main__':main()
