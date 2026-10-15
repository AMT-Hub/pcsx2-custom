import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from package_catalogue import DOCS, PREVIOUS_SHA, RUNTIME, package


class CatalogueUpdateTests(unittest.TestCase):
    def test_update_preserves_manual_settings_executables_and_runtime_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'PCSX2'
            protected = {
                'inis/sorting-titles.ini': b'[SCUS-97399_12345678]\nSortingTitle=My title\n',
                'Custom-PCSX2.exe': b'launcher sentinel',
                'custom-pcsx2/updater/active.txt': b'legacy\n',
                'custom-pcsx2/shader-prototype/pcsx2-qt.exe': b'runtime sentinel',
                'ShaderGlass/profile.sgp': b'profile sentinel',
            }
            for name, data in protected.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            archive = package(Path(tmp) / 'update.zip')
            with zipfile.ZipFile(archive) as z:
                self.assertIsNone(z.testzip())
                self.assertEqual([n for n in z.namelist() if not n.startswith(DOCS)], [RUNTIME])
                self.assertTrue(all('..' not in Path(n).parts and not n.startswith('/') for n in z.namelist()))
                z.extractall(root)
            for name, data in protected.items():
                self.assertEqual((root / name).read_bytes(), data)
            self.assertEqual((root / RUNTIME).read_bytes(), (ROOT / 'automatic-sorting.ini').read_bytes())
            rollback = (root / DOCS / 'rollback/automatic-sorting.ini').read_bytes()
            self.assertEqual(hashlib.sha256(rollback).hexdigest(), PREVIOUS_SHA)
            (root / RUNTIME).write_bytes(rollback)
            self.assertEqual((root / 'inis/sorting-titles.ini').read_bytes(), protected['inis/sorting-titles.ini'])


if __name__ == '__main__':
    unittest.main()
