"""Save accepted FrameSkip 0 / 4x defaults without rebuilding any executable."""
import argparse
import base64
import configparser
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

REPO = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('accepted_package', REPO/'ci/packages/automatic-sorting/package_personal.py')
base = importlib.util.module_from_spec(spec); spec.loader.exec_module(base)
sha, js, readzip, writezip = base.sha, base.js, base.readzip, base.writezip
INPUTS = {
    'PCSX2-Portable-0.9.0-Personal.zip': '26d459c557103cf6156c536c79c9a64496663a905255b1d7296731e6a6a2a3c5',
    'PCSX2-Nightly-2.9.127-AutoSort-0.2.0-Personal-1-of-2.zip': '891719d6925cd5279c0bba87f9282fc593c0c9dbce194af3355b7a04a201f703',
    'PCSX2-Nightly-2.9.127-AutoSort-0.2.0-Personal-2-of-2.zip': '00592681bb3a59569045da4fb9f763ee79646329b6ed3e26ddf5ce3b5aa5f499',
}
IDS = {'nightly-2_9_127-autosort-0_2_0':'nightly-2_9_127-autosort-pacing1',
       'nightly-2_9_127-ci1-test1':'nightly-2_9_127-ci1-pacing1'}

def set_resolution(raw):
    # Preserve INI formatting, repeated hotkey bindings and every unrelated byte.
    match = re.search(rb'(?m)^\[EmuCore/GS\]\r?\n(?P<body>[^\[]*)', raw)
    if not match: raise ValueError('Missing GS settings section')
    body, count = re.subn(rb'(?m)^upscale_multiplier\s*=\s*[^\r\n]+', b'upscale_multiplier = 4', match['body'])
    if count != 1: raise ValueError('Expected exactly one internal resolution setting')
    # Avoid rewriting even whitespace when the value is already correct.
    parsed=configparser.ConfigParser(interpolation=None,strict=False); parsed.read_string(raw.decode())
    if parsed['EmuCore/GS']['upscale_multiplier'] == '4': return raw
    return raw[:match.start('body')] + body + raw[match.end('body'):]

def finish(data, original, channel, policy, acceptance, source):
    profile=policy['profile_path']
    assert sha(original[profile])==policy['previous_profile_sha256']
    updated=(REPO/'defaults'/profile).read_bytes()
    assert sha(updated)==policy['profile_sha256']
    assert original[profile].replace(b'FrameSkip "1"',b'FrameSkip "0"')==updated
    data[profile]=updated
    data['inis/PCSX2.ini']=set_resolution(original['inis/PCSX2.ini'])
    for name,content in original.items():
        if name.startswith(base.PRESERVE) and name not in (profile,'inis/PCSX2.ini'):
            assert data[name]==content,name
    for name in ('Custom-PCSX2.exe','PCSX2-Update.exe'):
        if name in original: assert data[name]==original[name],name
    assert data['portable.txt']==original['portable.txt']
    assert len([n for n in data if n.startswith('bios/') and n.endswith('.bin')])==80
    assert len([n for n in data if n.startswith('gamesettings/') and n.endswith('.ini')])==30
    label='PCSX2 Portable 0.9.1 Personal (stable 2.8.2)' if channel=='stable' else 'PCSX2 Nightly 2.9.127 Personal r2'
    info=json.loads(data['PACKAGE-INFO.json']);info.update(release=label,shader_frame_skip=0,internal_resolution='4x Native (~1440px/QHD)',performance_defaults_accepted='2026-10-15',shader_profile_sha256=policy['profile_sha256'])
    if channel=='nightly': info.update(runtime_id=IDS[base.RID],previous_runtime=IDS[base.PREVIOUS])
    data['PACKAGE-INFO.json']=js(info)
    data['custom-pcsx2/performance-defaults-acceptance.json']=acceptance
    data['source/Performance-Defaults-20261015-Corresponding-Source.zip']=source
    readme=f'''{label}

Accepted defaults: ShaderGlass FrameSkip 0 and PCSX2 4x Native resolution.
The user confirmed noticeably smoother motion on 15 October 2026. The shader's
roughly 30-updates-per-second limit is removed; native 25/30 FPS games still
have their original game frame rates. The selected CRT shader is unchanged.

Extract all contents into a NEW writable folder and run Custom-PCSX2.exe.
For nightly, extract BOTH numbered ZIPs into the SAME new folder.
These are fresh-install packages. Do not overwrite an installation containing
your newer personal settings, saves or manual sorting edits with this archive.

All executable files and automatic sorting data are reused unchanged. Includes
all 80 supplied BIOS files, 30 per-game settings, Xbox profile/Guide pause,
compatibility-aware Auto BIOS, ShaderGlass and automatic/editable Sorting Titles.
Vulkan, Disallowed exclusive fullscreen and Fast Boot off are preserved.
4x Native was already present in the previous saved package and is retained.
Other exploratory performance suggestions have not been adopted as defaults.
Previous full archives are preserved separately.

The archive, payload hashes and signed nightly requirements were verified here.
No fresh Windows launch or updater UI install/rollback was performed here.
'''
    if channel=='nightly':
        readme+=f'''
Selected custom runtime: {IDS[base.RID]}
Rollback runtime: {IDS[base.PREVIOUS]}
The rollback runtime retains the older manual-only sorting implementation.
Both slots are signed for the corrected shader profile, so rollback does not
restore the old FrameSkip 1 limit. Their emulator payloads are unchanged.
The original vanilla pcsx2-qt.exe remains 2.9.126; use Custom-PCSX2.exe.

The online feed has NOT been changed. Its older packages require the old shader
profile and will be blocked by the existing dependency check. Do not restore
FrameSkip 1 just to install one. Future approved packages must use the new
profile hash. Keep PCSX2's built-in updater disabled.
'''
    data['START-HERE.txt']=readme.replace('\n','\r\n').encode();data['CURRENT-BUILD.md']=readme.encode()
    report={'date':'2026-10-15','channel':channel,'shader_frame_skip':0,'internal_resolution':4,'shader_profile_sha256':policy['profile_sha256'],'executables_unchanged':True,'automatic_sorting_catalogue_unchanged':True,'bios_files_preserved':80,'game_settings_preserved':30,'other_personal_configuration_unchanged':True,'new_windows_test_here':False}
    data['PROMOTION-VERIFICATION.json']=js(report)
    data['SHA256SUMS.json']=js({n:sha(v) for n,v in sorted(data.items()) if n!='SHA256SUMS.json'})
    return report

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--key',type=Path,required=True);a=p.parse_args()
    out=a.output;out.mkdir(parents=True,exist_ok=True)
    policy=json.loads((REPO/'defaults/performance.json').read_text())
    acceptance=(REPO/'ci/acceptance/2026-10-15-shader-pacing.json').read_bytes()
    paths=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard'],cwd=REPO,text=True).splitlines()
    source={n:(REPO/n).read_bytes() for n in paths if (REPO/n).is_file() and not n.startswith('.github/')}
    assert not any(n.endswith('.pem') or 'collection-titles' in n or 'COLLECTION-COVERAGE' in n for n in source)
    sourcefile=out/'PCSX2-Performance-Defaults-20261015-Source.zip'
    records=[writezip(sourcefile,source)];sourcebytes=sourcefile.read_bytes()
    (out/'retro-crisis_1080p-curved_PS2.sgp').write_bytes((REPO/'defaults'/policy['profile_path']).read_bytes())
    name='PCSX2-Portable-0.9.0-Personal.zip';original=readzip(a.input/name,INPUTS[name]);data=original.copy()
    reports=[finish(data,original,'stable',policy,acceptance,sourcebytes)]
    assert sha(data[base.LEGACY+'PCSX2-ShaderPrototype.exe'])==base.STABLE_EXE
    assert sha(data[base.LEGACY+'resources/automatic-sorting.ini'])==base.CATALOGUE
    records.append(writezip(out/'PCSX2-Portable-0.9.1-Personal.zip',data));del data,original
    original={}
    for name in list(INPUTS)[1:]:
        part=readzip(a.input/name,INPUTS[name]);assert not set(original)&set(part);original.update(part)
    xml=ET.fromstring(original['custom-pcsx2/updater/public-key.xml'])
    public=rsa.RSAPublicNumbers(int.from_bytes(base64.b64decode(xml.findtext('Exponent')),'big'),int.from_bytes(base64.b64decode(xml.findtext('Modulus')),'big')).public_key()
    private=serialization.load_pem_private_key(a.key.read_bytes(),password=None)
    assert private.public_key().public_numbers()==public.public_numbers()
    data={n:b for n,b in original.items() if not n.startswith('custom-pcsx2/runtimes/')}
    runtime_records=[]
    for old_id,new_id in IDS.items():
        oldslot='custom-pcsx2/runtimes/'+old_id+'/';slot='custom-pcsx2/runtimes/'+new_id+'/'
        raw=original[oldslot+'.release-manifest.json'];signature=original[oldslot+'.release-signature.bin']
        public.verify(signature,raw,padding.PKCS1v15(),hashes.SHA256());m=json.loads(raw);assert m['id']==old_id
        assert {n.removeprefix(oldslot) for n in original if n.startswith(oldslot)}==set(m['files'])|{'.release-manifest.json','.release-signature.bin'}
        for n,h in m['requires'].items(): assert sha(original[n])==h,n
        for n,r in m['files'].items():
            content=original[oldslot+n];assert sha(content)==r['sha256'] and len(content)==r['size'],n
            data[slot+n]=content
        m['id']=new_id;m['label']+=' - accepted smooth shader profile';m['requires'][policy['profile_path']]=policy['profile_sha256']
        raw=json.dumps(m,sort_keys=True,separators=(',',':')).encode();signature=private.sign(raw,padding.PKCS1v15(),hashes.SHA256())
        public.verify(signature,raw,padding.PKCS1v15(),hashes.SHA256())
        data[slot+'.release-manifest.json']=raw;data[slot+'.release-signature.bin']=signature
        runtime_records.append({'previous_id':old_id,'id':new_id,'runtime_payload_files':len(m['files']),'all_payload_bytes_unchanged':True,'new_signature_verified':True,'profile_requirement':policy['profile_sha256']})
    data['custom-pcsx2/updater/active.txt']=(IDS[base.RID]+'\n'+IDS[base.PREVIOUS]+'\n').encode()
    reports.append(finish(data,original,'nightly',policy,acceptance,sourcebytes))
    for rec in runtime_records:
        slot='custom-pcsx2/runtimes/'+rec['id']+'/'
        m=json.loads(data[slot+'.release-manifest.json'])
        for n,h in m['requires'].items(): assert sha(data[n])==h,n
        for n,r in m['files'].items(): assert sha(data[slot+n])==r['sha256'] and len(data[slot+n])==r['size'],n
        assert data[slot+'portable.txt'].strip()==b'../../..'
    current='custom-pcsx2/runtimes/'+IDS[base.RID]+'/'
    assert sha(data[current+'PCSX2-ShaderPrototype.exe'])==base.NIGHTLY_EXE
    assert sha(data[current+'resources/automatic-sorting.ini'])==base.CATALOGUE
    part2={n:b for n,b in data.items() if n.startswith('custom-pcsx2/runtimes/')};part1={n:b for n,b in data.items() if n not in part2}
    records.append(writezip(out/'PCSX2-Nightly-2.9.127-Personal-r2-1-of-2.zip',part1))
    records.append(writezip(out/'PCSX2-Nightly-2.9.127-Personal-r2-2-of-2.zip',part2))
    report={'input_archives':INPUTS,'artifacts':records,'settings':policy,'verification':reports,'nightly_signatures':runtime_records,'live_feed_changed':False,'previous_archives_overwritten':False}
    (out/'PERFORMANCE-DEFAULTS-VERIFICATION.json').write_bytes(js(report))
    (out/'SHA256SUMS.txt').write_text(''.join(r['sha256']+'  '+r['filename']+'\n' for r in records)+sha((out/'retro-crisis_1080p-curved_PS2.sgp').read_bytes())+'  retro-crisis_1080p-curved_PS2.sgp\n')
    print('Updated defaults saved; both nightly signatures and all preserved payloads verified.',flush=True)

if __name__=='__main__':main()
