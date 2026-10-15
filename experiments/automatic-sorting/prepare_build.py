"""Generate disposable build kits. Never edit accepted emulator/ build inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]


def replace(path, old, new):
    text = path.read_text(encoding='utf-8')
    if text.count(old) != 1:
        raise ValueError('Unexpected build input: ' + str(path) + ' / ' + old[:60])
    path.write_text(text.replace(old, new), encoding='utf-8', newline='\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('channel', choices=['stable','nightly'])
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    dest = args.destination.resolve()
    if dest.exists():
        raise ValueError('Use a new build folder: ' + str(dest))
    shutil.copytree(REPO / 'emulator', dest, ignore=shutil.ignore_patterns('work','__pycache__','*.zip','*.7z','Build.log'))
    for name in ('apply-automatic-sorting.py','AutoSortTitle.h','automatic-sorting.ini','catalogue.json'):
        shutil.copyfile(ROOT / name, dest / name)
    shutil.copytree(ROOT / 'tests', dest / 'automatic-tests', ignore=shutil.ignore_patterns('__pycache__'))
    if args.channel == 'stable':
        # The accepted stable kit builds a minimal EXE overlay from pinned source.
        # It does not consume an official prebuilt archive or replace patches.zip.
        shutil.copyfile(ROOT/'stable-baseline/build.py', dest/'build.py')
        replace(dest/'build.py', "        run([sys.executable, ROOT / 'autobios-test/apply-patch.py', SOURCE])", "        run([sys.executable, ROOT / 'verify-upstream.py', SOURCE])\n        run([sys.executable, ROOT / 'autobios-test/apply-patch.py', SOURCE])")
        shutil.copyfile(ROOT/'stable-baseline/upstream-shader-hashes.json', dest/'upstream-shader-hashes.json')
        shutil.copyfile(ROOT/'stable-baseline/autobios-upstream-sha256.json', dest/'autobios-test/upstream-sha256.json')
        shutil.copyfile(ROOT/'stable-baseline/upstream-integration-sha256.json', dest/'nightly-upstream-sha256.json')
    # Include all newly touched original files in the existing source gate.
    hashes=json.loads((dest/'nightly-upstream-sha256.json').read_text())
    hashes.update(json.loads((ROOT/(args.channel+'-sorting-upstream-sha256.json')).read_text()))
    (dest/'nightly-upstream-sha256.json').write_text(json.dumps(hashes,indent=2)+'\n')
    replace(dest/'build.py', "run([sys.executable, ROOT / 'apply-sorting-patch.py', SOURCE])", "run([sys.executable, ROOT / 'apply-sorting-patch.py', SOURCE])\n        run([sys.executable, ROOT / 'apply-automatic-sorting.py', SOURCE])")
    replace(dest/'build.py', '        save_shader_stamp(shader_source)', "        files += ['pcsx2/AutoSortTitle.h', 'pcsx2-qt/GameList/GameListModel.cpp', 'bin/resources/automatic-sorting.ini']\n        save_shader_stamp(shader_source)")
    replace(dest/'build.py', "    run([WORK / 'policy-test.exe'])", "    run([WORK / 'policy-test.exe'])\n    run([compiler, '/nologo', '/std:c++17', '/EHsc', ROOT / 'automatic-tests/policy.cpp', '/Fe:' + str(WORK / 'auto-sort-policy.exe'), '/Fo:' + str(WORK / 'auto-sort-policy.obj')])\n    run([WORK / 'auto-sort-policy.exe'])")
    replace(dest/'build.py', "'status': 'compiled; Windows acceptance tests required'", "'automatic_sorting': '0.1.0-test1', 'channel': '"+args.channel+"',\n                'status': 'experimental; Windows acceptance tests required'")
    print('Prepared isolated',args.channel,'kit:',dest)


if __name__ == '__main__':
    main()
