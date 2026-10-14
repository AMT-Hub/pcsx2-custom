"""Read-only source gate. Passing permits a build, never release approval."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

REPO = Path(__file__).resolve().parents[1]


def literal(path, name):
    for node in ast.parse(path.read_text(encoding='utf-8')).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise ValueError(f'Missing constant {name} in {path}')


def validate_tag(tag):
    if not re.fullmatch(r'v2\.[0-9]{1,4}\.[0-9]{1,6}', tag):
        raise ValueError('Use an official version tag, for example v2.9.126.')
    return tag


def compare(source, expected):
    changes = []
    for name, digest in sorted(expected.items()):
        path = source / name
        actual = hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest() if path.is_file() and not path.is_symlink() else None
        if actual != digest:
            changes.append({'file': name, 'expected': digest, 'actual': actual})
    return changes


def assess(source, tag):
    validate_tag(tag)
    commit = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    tagged = subprocess.check_output(['git', '-C', str(source), 'rev-parse', f'refs/tags/{tag}^{{commit}}'], text=True).strip()
    if tagged != commit:
        raise ValueError('Checkout does not match the requested tag.')
    if subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain'], text=True).strip():
        raise ValueError('Candidate source checkout must be clean.')
    baseline = literal(REPO / 'emulator/build.py', 'COMMIT')
    archive = literal(REPO / 'emulator/assemble.py', 'NIGHTLY')
    baseline_tag = archive.removeprefix('pcsx2-').removesuffix('-windows-x64-Qt.7z')
    changes = compare(source, json.loads((REPO / 'emulator/nightly-upstream-sha256.json').read_text()))
    permitted = commit == baseline and tag == baseline_tag and not changes
    return {'schema': 1, 'tag': tag, 'commit': commit, 'reviewed_commit': baseline,
            'status': 'ready-for-build' if permitted else 'review-required',
            'build_permitted': permitted, 'release_approved': False,
            'changed_integration_files': changes,
            'reason': 'Exact reviewed source; compilation and Windows acceptance still required.' if permitted else
                      'Unreviewed version or changed integration files. Port/review the build kit before building. Unchanged integration files alone do not establish compatibility.',
            'official_archive': archive,
            'official_archive_sha256': literal(REPO / 'emulator/assemble.py', 'EXPECTED')}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tag', required=True)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--report', type=Path, default=Path('candidate-report.json'))
    args = parser.parse_args()
    validate_tag(args.tag)
    if not args.source:
        print('Validated version tag:', args.tag)
        return
    report = assess(args.source, args.tag)
    args.report.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    summary = f"## Candidate {report['tag']}\n\n**{report['status']}**\n\n{report['reason']}\n\nCommit: `{report['commit']}`\n\n"
    if report['changed_integration_files']:
        summary += 'Changed integration files:\n' + ''.join(f"- `{item['file']}`\n" for item in report['changed_integration_files'])
    summary += '\nNo signing, release publication or approved-feed changes are performed by this workflow.\n'
    args.report.with_suffix('.md').write_text(summary, encoding='utf-8')
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as f:
            f.write(summary)
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as f:
            f.write('build_permitted=' + str(report['build_permitted']).lower() + '\n')
    print(summary)


if __name__ == '__main__':
    main()
