"""A data-only update shared by the stable and nightly sorting test runtimes."""
import argparse
import hashlib
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent
RUNTIME = 'custom-pcsx2/shader-prototype/resources/automatic-sorting.ini'
DOCS = 'custom-pcsx2/automatic-sorting-0.2.0-test1/'
PREVIOUS_SHA = '35590be83c41aed3d1c174e89ce40f69f70fb17670fc1f07ae416a862036dd2c'


def package(destination, private_report_dir=None):
    previous = (ROOT / 'previous-catalogue/automatic-sorting-0.1.0-test1.ini').read_bytes()
    if hashlib.sha256(previous).hexdigest() != PREVIOUS_SHA:
        raise ValueError('Rollback catalogue changed')
    files = {RUNTIME: (ROOT / 'automatic-sorting.ini').read_bytes(),
             DOCS + 'rollback/automatic-sorting.ini': previous}
    for name in ('README.md', 'RULES-COVERAGE.json', 'VALIDATION.json', 'RESEARCH.md'):
        files[DOCS + name] = (ROOT / name).read_bytes()
    if private_report_dir:
        for name in ('COLLECTION-COVERAGE.md', 'COLLECTION-COVERAGE.json'):
            files[DOCS + name] = (Path(private_report_dir) / name).read_bytes()
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for path, payload in sorted(files.items()):
            entry = zipfile.ZipInfo(path, date_time=(2026, 10, 15, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            z.writestr(entry, payload)
    return destination


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--private-report-dir', type=Path, help='Include private reports only in the personal download, never public source.')
    args = p.parse_args()
    path = package(args.output, args.private_report_dir)
    print(path)
    print('SHA256', hashlib.sha256(path.read_bytes()).hexdigest())
