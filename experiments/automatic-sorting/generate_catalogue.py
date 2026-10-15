"""Resolve reviewed aliases into explicit serial identities, never at runtime.

Requires PyYAML only when regenerating from the pinned upstream GameIndex. The
emulator reads the generated INI and never needs Python, a network, or ROM paths.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import re
import unicodedata

ROOT = Path(__file__).resolve().parent
RETAIL_TAGS = {
    'greatest hits', 'platinum', 'playstation2 the best', 'playstation 2 the best',
    'playstation 2 the best - reprint', 'ultimate hits', 'mega hits!',
    'ea best hits', 'takara the best', 'atlus best collection',
    'special gift package', 'ps2 bundle', 'collector\'s edition',
    'playstation 2 bighit series', 'jenny hi-grade box', 'dx hunters box',
    'disc 1 of 2', 'disc 2 of 2', 'with bonus dvd', 'entry disc',
}


def normalise(title):
    title = unicodedata.normalize('NFKC', title).casefold().strip()
    tags = re.findall(r'\[([^\]]+)\]', title)
    if any(tag not in RETAIL_TAGS for tag in tags):
        return None  # No guessing across demos, betas, compilations or editions.
    title = re.sub(r'\[[^\]]+\]', '', title)
    return ' '.join(re.sub(r'[^\w]+', ' ', title).split())


def generate(seed, index):
    aliases, identities, games = {}, {}, []
    for game in seed['games']:
        if any(old['id'] == game['id'] for old in games):
            raise ValueError('Duplicate game id: ' + game['id'])
        title = game['sorting_title']
        if not title or len(title) > 256 or any(ch in title for ch in '\r\n\x00'):
            raise ValueError('Invalid sorting title')
        for alias in game['aliases']:
            key = normalise(alias)
            if not key or (key in aliases and aliases[key] != game['id']):
                raise ValueError('Ambiguous or repeated alias: ' + alias)
            aliases[key] = game['id']
        games.append({**game, 'identities': []})
    by_id = {game['id']: game for game in games}
    for serial, entry in index.items():
        matches = {aliases[n] for field in ('name', 'name-en')
                   if (n := normalise(entry.get(field, ''))) in aliases}
        matches.update(game['id'] for game in games if serial in game.get('serials', []))
        if len(matches) > 1:
            raise ValueError('Conflicting identities for ' + serial)
        if matches:
            if not re.fullmatch('[A-Z0-9]+-[A-Z0-9]+', serial):
                raise ValueError('Unexpected serial: ' + serial)
            game = by_id[next(iter(matches))]
            record = {'serial': serial, 'name': entry['name'], 'region': entry.get('region', ''),
                      'english_name': entry.get('name-en', '')}
            game['identities'].append(record)
            identities[serial] = game['sorting_title']
    for game in games:
        if not game['identities']:
            raise ValueError('No identities matched: ' + game['id'])
        for serial in game.get('serials', []):
            if serial not in index:
                raise ValueError('Unknown explicit serial: ' + serial)
    return games, identities


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('gameindex', type=Path, nargs='?', help='Optional pinned source verification; normal builds use the checked-in facts snapshot.')
    args = parser.parse_args()
    seed = json.loads((ROOT / 'catalogue-seed.json').read_text(encoding='utf-8'))
    if args.gameindex:
        raw = args.gameindex.read_bytes().replace(b'\r\n', b'\n')
        if hashlib.sha256(raw).hexdigest() != seed['upstream_gameindex_sha256']:
            raise ValueError('Use the pinned upstream GameIndex; changed data requires review.')
    from rules import compile_defaults, retail
    snapshot_bytes=(ROOT/'identity-metadata.json.gz').read_bytes()
    metadata=json.loads(gzip.decompress(snapshot_bytes))
    provenance=json.loads((ROOT/'METADATA-PROVENANCE.json').read_text())
    if hashlib.sha256(snapshot_bytes).hexdigest()!=provenance['snapshot_sha256']:
        raise ValueError('Metadata snapshot checksum mismatch')
    records=metadata['records']
    index={r['serial']:{'name':r['name'],'name-en':r['english_name'],'region':r['region']} for r in records}
    games, exceptions = generate(seed, index)
    for game in games:
        game['identities']=[i for i in game['identities'] if retail(i['serial'],i['english_name'] or i['name'])]
    policy=json.loads((ROOT/'rules.json').read_text())
    identities, reasons, unresolved=compile_defaults(records,policy,exceptions)
    coverage={'source_identities':len(records),'eligible_identities':len(identities),'excluded_nonretail':len(records)-len(identities),'by_rule':dict(Counter(reasons.values())),'unresolved_franchise_members':unresolved,'coverage_limit':'Every eligible known serial receives a default. A normalised title is not proof that franchise chronology is known; unsupported identities retain the existing emulator fallback.'}
    (ROOT / 'catalogue.json').write_text(json.dumps({**seed, 'games': games,'coverage':coverage}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    for serial, title in identities.items():
        if not re.fullmatch('[A-Z0-9]+-[A-Z0-9]+', serial) or not title or any(ch in title for ch in '\r\n\x00'):
            raise ValueError('Unsafe INI identity/title: ' + repr(serial))
    ini = f'; Automatic Sorting Titles catalogue {seed["version"]}; generated from rules, metadata and user exceptions\n; Manual overrides belong in inis/sorting-titles.ini, not this file.\n\n'
    ini += ''.join(f'[{serial}]\nSortingTitle = {title}\n\n' for serial, title in sorted(identities.items()))
    (ROOT / 'automatic-sorting.ini').write_text(ini, encoding='utf-8', newline='\n')
    (ROOT/'RULES-COVERAGE.json').write_text(json.dumps({'version':policy['version'],**coverage},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'version':policy['version'],**{k:v for k,v in coverage.items() if k!='unresolved_franchise_members'},'unresolved_franchise_members':len(unresolved)},indent=2))


if __name__ == '__main__':
    main()
