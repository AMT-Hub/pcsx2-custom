"""Review expected database identities; never pretend filenames prove ROM CRCs."""
from collections import defaultdict
import argparse
import gzip
import json
from pathlib import Path
from generate_catalogue import generate
from rules import compile_defaults, key, retail

ROOT = Path(__file__).resolve().parent


def main(input_path, output_dir):
    records = json.loads(gzip.decompress((ROOT / 'identity-metadata.json.gz').read_bytes()))['records']
    index = {r['serial']: {'name': r['name'], 'name-en': r['english_name'], 'region': r['region']} for r in records}
    _, exceptions = generate(json.loads((ROOT / 'catalogue-seed.json').read_text()), index)
    defaults, reasons, _ = compile_defaults(records, json.loads((ROOT / 'rules.json').read_text()), exceptions)
    lookup = defaultdict(list)
    for r in records:
        if not retail(r['serial'], r['english_name'] or r['name']):
            continue
        for name in {key(r['name']), key(r['english_name'])} - {''}:
            lookup[name].append(r)
    aliases = {
        'Ratchet & Clank - Going Commando': 'Ratchet & Clank 2 - Going Commando',
        'Ookami': 'Okami',
    }
    regions = {'USA': 'NTSC-U', 'Europe': 'PAL', 'Japan': 'NTSC-J'}
    prefixes = {'USA': ('SCUS-', 'SLUS-'), 'Europe': ('SCES-', 'SLES-'), 'Japan': ('SCPS-', 'SLPS-', 'SLPM-')}
    review = []
    for line in input_path.read_text().splitlines():
        title, region, *notes = line.split('\t')
        query = 'ChoroQ' if title == 'Choro Q' and region == 'USA' else aliases.get(title, title)
        matches = [r for r in lookup[key(query)] if r['region'].startswith(regions[region])]
        local = [r for r in matches if r['serial'].startswith(prefixes[region])]
        if local:
            matches = local
        if '[' in query:
            matches = [r for r in matches if query in (r['name'], r['english_name'])]
        review.append({'title': title, 'region': region, 'notes': ' '.join(notes),
                       'expected': [{'serial': r['serial'], 'sorting_title': defaults[r['serial']],
                                     'rule': reasons[r['serial']]} for r in matches]})
    missing = [r for r in review if not r['expected']]
    if missing:
        raise ValueError('Unresolved collection titles: ' + repr(missing))
    summary = {'collection_entries': len(review), 'matched_entries': len(review) - len(missing),
               'actual_disc_identity_verified': False,
               'limit': 'Expected stock database identities only. No ROM bytes or CRC inventory were supplied; patches may change identity. BIN/CUE pairs count once.'}
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / 'COLLECTION-COVERAGE.json').write_text(json.dumps({'summary': summary, 'games': review}, ensure_ascii=False, indent=2) + '\n')
    lines = ['# Collection audit — 0.2.0-test1', '',
             f"All {len(review)} supplied collection entries have an expected database match.", '',
             summary['limit'], '',
             'A default identical to the display title is ordinary title coverage, not a claim that the entire franchise chronology is known. Manual edits override every result below.', '',
             '| Supplied title | Region | Expected Sorting Title | Method |',
             '| --- | --- | --- | --- |']
    for row in review:
        values = sorted({r['sorting_title'] for r in row['expected']})
        methods = sorted({r['rule'] for r in row['expected']})
        lines.append('| ' + ' | '.join([row['title'], row['region'], '; '.join(values), ', '.join(methods)]) + ' |')
    lines += ['', '## Identity caveats', '']
    lines += ['- ' + r['title'] + ': ' + r['notes'] for r in review if r['notes']]
    lines += ['', 'Full expected serials are in COLLECTION-COVERAGE.json. This report does not alter settings or inspect game files.', '']
    (output_dir / 'COLLECTION-COVERAGE.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--input', type=Path, required=True, help='Private TSV: title, region, optional note.')
    p.add_argument('--output', type=Path, required=True, help='Private audit output directory.')
    args = p.parse_args()
    main(args.input, args.output)
