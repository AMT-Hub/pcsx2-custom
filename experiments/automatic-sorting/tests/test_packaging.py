import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]


class PackagingTests(unittest.TestCase):
    def test_test_copy_uses_supported_manual_runtime_without_forged_approval(self):
        for channel in ('stable', 'nightly'):
            with self.subTest(channel=channel), tempfile.TemporaryDirectory() as temporary:
                kit = Path(temporary)
                stage = kit / 'work/package'
                (stage / 'resources').mkdir(parents=True)
                (stage / 'PCSX2-ShaderPrototype.exe').write_bytes(b'test executable fixture')
                (stage / 'resources/automatic-sorting.ini').write_bytes(b'; fixture\n')
                (stage / 'BUILD-INFO.json').write_text('{}')
                (stage / 'portable.txt').write_text('WRONG INITIAL PATH')
                (kit / 'policy').mkdir()
                for name in ('auto-bios.enabled','bios-catalogue.tsv','bios-rules.tsv'):
                    (kit / 'policy' / name).write_text('fixture')
                subprocess.run([sys.executable, str(ROOT/'package_test.py'), channel, str(kit)],
                               check=True, stdout=subprocess.DEVNULL)
                with zipfile.ZipFile(next(kit.glob('*overlay.zip'))) as z:
                    names = set(z.namelist())
                    self.assertIn('custom-pcsx2/shader-prototype/PCSX2-ShaderPrototype.exe', names)
                    self.assertNotIn('Custom-PCSX2.exe', names)
                    self.assertFalse(any('/runtimes/' in n or 'release-manifest' in n or 'signature' in n for n in names))
                    self.assertFalse(any(n.startswith(('inis/','bios/','gamesettings/','memcards/')) for n in names))
                    self.assertNotIn('custom-pcsx2/updater/active.txt', names)
                    if channel == 'nightly':
                        self.assertEqual(z.read('custom-pcsx2/shader-prototype/portable.txt').strip(),b'../..')
                    else:
                        self.assertNotIn('custom-pcsx2/shader-prototype/portable.txt',names)
                    manifest=json.loads(z.read('AUTOMATIC-SORTING-TEST-HASHES.json'))
                    for n,h in manifest.items():
                        self.assertEqual(hashlib.sha256(z.read(n)).hexdigest(),h)


if __name__=='__main__':unittest.main()
