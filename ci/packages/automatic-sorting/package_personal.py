"""Promote exact accepted components into private, full portable archives.

Requires previously saved personal baselines. Never upload its personal outputs
to the public repository. The signing key stays outside all staged archives.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

REPO = Path(__file__).resolve().parents[3]
CATALOGUE = '3c585c804f30ac3b175d38af3be251c92bdf6789ece4463e9321e420031e7276'
STABLE_EXE = '822703539dcdfad314c68c8ba3ff318564eb1aaf14552bb29ee3a17d6f8f3d9a'
NIGHTLY_EXE = 'c8411bb8ef9cf89a84df0792f1851034b92f7f046ead62c5fc249e51950d996e'
RID = 'nightly-2_9_127-autosort-0_2_0'
PREVIOUS = 'nightly-2_9_127-ci1-test1'
LEGACY = 'custom-pcsx2/shader-prototype/'
PRESERVE = ('bios/', 'inis/', 'gamesettings/', 'inputprofiles/', 'ShaderGlass/')

def sha(b): return hashlib.sha256(b).hexdigest()
def js(d): return (json.dumps(d, indent=2) + '\n').encode()
def readzip(p, expected=None):
    if expected:
        with p.open('rb') as f: assert hashlib.file_digest(f, 'sha256').hexdigest() == expected, p
    with zipfile.ZipFile(p) as z:
        assert len(z.namelist()) == len(set(z.namelist()))
        assert all(not n.startswith(('/', '\\')) and '..' not in Path(n).parts for n in z.namelist())
        return {n: z.read(n) for n in z.namelist() if not n.endswith('/')}

def writezip(p, data):
    with zipfile.ZipFile(p, 'x', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for n, b in sorted(data.items()): z.writestr(n, b)
    with zipfile.ZipFile(p) as z:
        assert set(z.namelist()) == set(data)
        for n, b in data.items(): assert z.read(n) == b, n
    with p.open('rb') as f: digest = hashlib.file_digest(f, 'sha256').hexdigest()
    record = {'filename': p.name, 'bytes': p.stat().st_size, 'sha256': digest}
    print(json.dumps(record), flush=True)
    return record

def finish(data, original, channel, source, acceptance):
    for n, b in original.items():
        if n.startswith(PRESERVE): assert data[n] == b, n
    assert len([n for n in data if n.startswith('bios/') and n.endswith('.bin')]) == 80
    assert len([n for n in data if n.startswith('gamesettings/') and n.endswith('.ini')]) == 30
    data['portable.txt'] = b''
    data['source/Automatic-Sorting-0.2.0-Corresponding-Source.zip'] = source
    data['custom-pcsx2/automatic-sorting-acceptance.json'] = acceptance
    label = '0.9.0 Personal (PCSX2 2.8.2)' if channel == 'stable' else 'Nightly 2.9.127 Personal - Automatic Sorting 0.2.0'
    readme = f'''Custom PCSX2 {label}

Current working build: Automatic Sorting Titles accepted on 15 October 2026.
Extract all contents into a NEW writable folder and run Custom-PCSX2.exe.
For the nightly download, extract BOTH numbered ZIPs into the SAME folder.
These are full fresh installations, not overlays for an existing installation.
Your already tested installation does not need replacing just to mark acceptance.

Exact tested emulator EXE and catalogue bytes are preserved. Historical test1
labels in the tooltip/build info are retained to avoid rebuilding accepted code.
Automatic defaults cover 11,458 disc identities. Manual Sorting Titles win over
defaults and survive rescans, new game folders and runtime updates. Clear a
Sorting Title to opt out; right-click its field to restore automatic sorting.

Includes the existing 80 BIOS files, 30 game settings, Xbox profile/Guide pause,
compatibility Auto BIOS, ShaderGlass, taskbar identity and portable defaults.
Vulkan, exclusive fullscreen Disallowed and Fast Boot off remain unchanged.
First-run setup selects your ROM directories. Saves and edits made in your own
installed copy are not present in this fresh archive. Keep that copy backed up.

Previous accepted archives remain available separately. Package checks verify
hashes, signatures, all runtime files and preservation of personal defaults.
This reassembled full archive has not received a separate Windows launch here.
'''
    if channel == 'nightly':
        readme += f'''
Custom launcher selects signed runtime {RID}.
Roll back selects the earlier accepted custom 2.9.127 runtime (without automatic
sorting); a second rollback returns to this version. The original vanilla
pcsx2-qt.exe remains 2.9.126. Use Custom-PCSX2.exe for the custom functionality.
The hosted update feed is separately published and may still show the previous
2.9.127 release. Do not install that older release expecting automatic sorting.
Keep the official PCSX2 updater disabled. The separate signed sorting update ZIP
can be installed through PCSX2-Update.exe > Install local ZIP in a matching copy.
'''
    data['START-HERE.txt'] = readme.replace('\n', '\r\n').encode()
    data['CURRENT-BUILD.md'] = readme.encode()
    info = json.loads(data['PACKAGE-INFO.json'])
    info.update(release=label, automatic_sorting_titles='0.2.0', status='user-accepted sorting; exact tested EXE/catalogue reused', catalogue_sha256=CATALOGUE)
    if channel == 'nightly': info.update(runtime_id=RID, previous_runtime=PREVIOUS)
    data['PACKAGE-INFO.json'] = js(info)
    data.pop('BASELINE-VERIFICATION.json', None)
    data['PROMOTION-VERIFICATION.json'] = js({'date':'2026-10-15', 'channel':channel, 'catalogue_sha256':CATALOGUE, 'bios_files_preserved':80, 'game_settings_preserved':30, 'personal_defaults_unchanged':True, 'recompiled':False, 'fresh_windows_launch_here':False})
    data['SHA256SUMS.json'] = js({n: sha(b) for n, b in sorted(data.items()) if n != 'SHA256SUMS.json'})

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--workspace', required=True, type=Path)
    p.add_argument('--key', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args(); w = a.workspace; out = a.output
    out.mkdir(parents=True, exist_ok=True)
    catalogue = (REPO/'experiments/automatic-sorting/automatic-sorting.ini').read_bytes()
    assert sha(catalogue) == CATALOGUE
    acceptance = (REPO/'ci/acceptance/2026-10-15-automatic-sorting.json').read_bytes()
    paths = subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard'], cwd=REPO, text=True).splitlines()
    source = {n:(REPO/n).read_bytes() for n in paths if (REPO/n).is_file() and not n.startswith('.github/')}
    assert not any(n.endswith('.pem') or 'collection-titles' in n or 'COLLECTION-COVERAGE' in n for n in source)
    sourcefile = out/'PCSX2-Automatic-Sorting-0.2.0-Corresponding-Source.zip'
    records = [writezip(sourcefile, source)]
    sourcebytes = sourcefile.read_bytes()
    stable = readzip(w/'baseline-downloads/PCSX2-Portable-0.8.0-Personal.zip','387d569e60d942490613db826e1c3000f9fe2ef7602f59526be8fa5608d63b58')
    data = stable.copy()
    overlay = readzip(w/'sorting-deliverables/PCSX2-Automatic-Sorting-stable-0.1.0-test1-overlay.zip','b3225c2bbd0db7d2ce81a132b99dcb73c634224071472e146221b44589092d34')
    data.update({n:b for n,b in overlay.items() if n.startswith(LEGACY)})
    data[LEGACY+'resources/automatic-sorting.ini'] = catalogue
    assert sha(data[LEGACY+'PCSX2-ShaderPrototype.exe']) == STABLE_EXE
    assert data[LEGACY+'portable.txt'].strip() == b'../..'
    finish(data, stable, 'stable', sourcebytes, acceptance)
    records.append(writezip(out/'PCSX2-Portable-0.9.0-Personal.zip', data))
    del data, stable, overlay
    original = readzip(w/'baseline-deliverables/PCSX2-Nightly-2.9.127-Personal-Baseline.zip')
    xml = ET.fromstring(original['custom-pcsx2/updater/public-key.xml'])
    public = rsa.RSAPublicNumbers(int.from_bytes(base64.b64decode(xml.findtext('Exponent')),'big'),int.from_bytes(base64.b64decode(xml.findtext('Modulus')),'big')).public_key()
    private = serialization.load_pem_private_key(a.key.read_bytes(), password=None)
    assert private.public_key().public_numbers() == public.public_numbers(), 'Wrong signing key.'
    overlay = readzip(w/'sorting-deliverables/PCSX2-Automatic-Sorting-nightly-0.1.0-test1-overlay.zip','e390e57710b68e9d994ac6d5ea89eb1e2e8cd376ed3d8955f4c70b92eb6aa842')
    runtime = {n.removeprefix(LEGACY):b for n,b in overlay.items() if n.startswith(LEGACY)}
    assert sha(runtime['PCSX2-ShaderPrototype.exe']) == NIGHTLY_EXE
    runtime['resources/automatic-sorting.ini'] = catalogue
    runtime['portable.txt'] = b'../../..\r\n'
    stage = out/'signing-stage'; stage.mkdir()
    for n,b in runtime.items():
        target=stage/n;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b)
    deps=out/'required-dependencies'
    for n in ['ShaderGlass/ShaderGlass-PCSX2.exe','ShaderGlass/Profiles/retro-crisis_1080p-curved_PS2.sgp']:
        target=deps/n;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(original[n])
    signed=out/'PCSX2-Nightly-2.9.127-Automatic-Sorting-0.2.0-Signed-Update.zip'
    subprocess.run([sys.executable,REPO/'publisher/make_package.py','--runtime',stage,'--root',deps,'--key',a.key,'--id',RID,'--label','PCSX2 2.9.127 - Automatic Sorting 0.2.0','--output',signed,'--approve-tested-release'],check=True)
    package=readzip(signed)
    public.verify(package['manifest.sig'],package['manifest.json'],padding.PKCS1v15(),hashes.SHA256())
    manifest=json.loads(package['manifest.json']);assert manifest['id']==RID
    assert set(manifest['files'])==set(runtime)
    for n,b in runtime.items(): assert manifest['files'][n]=={'size':len(b),'sha256':sha(b)} and package['runtime/'+n]==b,n
    for n,h in manifest['requires'].items(): assert sha(original[n])==h,n
    oldslot='custom-pcsx2/runtimes/'+PREVIOUS+'/'
    public.verify(original[oldslot+'.release-signature.bin'],original[oldslot+'.release-manifest.json'],padding.PKCS1v15(),hashes.SHA256())
    oldmanifest=json.loads(original[oldslot+'.release-manifest.json'])
    for n,r in oldmanifest['files'].items(): assert sha(original[oldslot+n])==r['sha256'],n
    data={n:b for n,b in original.items() if not n.startswith(LEGACY)}
    slot='custom-pcsx2/runtimes/'+RID+'/'
    data.update({slot+n:b for n,b in runtime.items()})
    data[slot+'.release-manifest.json']=package['manifest.json'];data[slot+'.release-signature.bin']=package['manifest.sig']
    data['custom-pcsx2/updater/active.txt']=(RID+'\n'+PREVIOUS+'\n').encode()
    assert sha(data['Custom-PCSX2.exe'])=='4fab61885b8aa0fa413255b5d1927d6a785ef52e99e68203dc52d08828f147f9'
    assert data['PCSX2-Update.exe']==original['PCSX2-Update.exe']
    finish(data, original, 'nightly', sourcebytes, acceptance)
    # Two ordinary non-overlapping ZIPs, each below the download size limit.
    # Both extract at the portable root; neither is a multi-volume ZIP format.
    part2={n:b for n,b in data.items() if n.startswith('custom-pcsx2/runtimes/')}
    part1={n:b for n,b in data.items() if n not in part2}
    assert not set(part1)&set(part2) and set(part1)|set(part2)==set(data)
    records.append(writezip(out/'PCSX2-Nightly-2.9.127-AutoSort-0.2.0-Personal-1-of-2.zip',part1))
    records.append(writezip(out/'PCSX2-Nightly-2.9.127-AutoSort-0.2.0-Personal-2-of-2.zip',part2))
    records.append({'filename':signed.name,'bytes':signed.stat().st_size,'sha256':sha(signed.read_bytes())})
    (out/'SHA256SUMS.txt').write_text(''.join(r['sha256']+'  '+r['filename']+'\n' for r in records))
    (out/'PROMOTION-REPORT.json').write_bytes(js({'artifacts':records,'catalogue_sha256':CATALOGUE,'stable_executable_sha256':STABLE_EXE,'nightly_executable_sha256':NIGHTLY_EXE,'new_runtime_id':RID,'rollback_runtime_id':PREVIOUS,'signature_and_all_payload_hashes_verified':True,'bios_files_preserved':80,'game_settings_preserved':30,'personal_defaults_unchanged':True,'private_signing_material_excluded':True,'live_feed_changed':False,'new_windows_launch_here':False}))
    print('Promotion assembly and byte verification complete.',flush=True)

if __name__=='__main__': main()
