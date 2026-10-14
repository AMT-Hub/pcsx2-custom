import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import assess_candidate as gate


class GateTests(unittest.TestCase):
    def test_rejects_refs_and_shell_fragments(self):
        for value in ['main', '../v2.9.126', 'v2.9.126;echo bad', 'v2.9.126\n', '--help', 'v2.9.126/other']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                gate.validate_tag(value)

    def test_missing_changed_and_newlines(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'ok').write_bytes(b'hello\r\n')
            (root / 'changed').write_bytes(b'bad')
            digest = hashlib.sha256(b'hello\n').hexdigest()
            result = gate.compare(root, {'ok': digest, 'changed': digest, 'missing': digest})
            self.assertEqual([r['file'] for r in result], ['changed', 'missing'])

    def test_new_commit_never_autoapproved(self):
        baseline = gate.literal(gate.REPO / 'emulator/build.py', 'COMMIT')
        archive = gate.literal(gate.REPO / 'emulator/assemble.py', 'NIGHTLY')
        reviewed_tag = archive.removeprefix('pcsx2-').removesuffix('-windows-x64-Qt.7z')
        unreviewed_tag = 'v2.9999.999999'
        for sha, tag, changes, permitted in [(baseline, reviewed_tag, [], True), ('f'*40, unreviewed_tag, [], False),
                                              ('f'*40, reviewed_tag, [], False),
                                              (baseline, reviewed_tag, [{'file': 'x'}], False),
                                              (baseline, unreviewed_tag, [], False)]:
            with patch.object(subprocess, 'check_output', side_effect=[sha, sha, '']), patch.object(gate, 'compare', return_value=changes):
                result = gate.assess(Path('unused'), tag)
                self.assertEqual(result['build_permitted'], permitted)
                self.assertFalse(result['release_approved'])

    def test_dirty_or_wrong_tag_fails(self):
        for outputs in [('a'*40, 'b'*40), ('a'*40, 'a'*40, ' M modified')]:
            with patch.object(subprocess, 'check_output', side_effect=outputs), self.assertRaises(ValueError):
                gate.assess(Path('unused'), 'v2.9.126')


if __name__ == '__main__':
    unittest.main()
