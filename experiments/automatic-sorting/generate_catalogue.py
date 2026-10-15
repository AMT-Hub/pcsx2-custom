"""Resolve reviewed aliases into explicit serial identities, never at runtime.

Requires PyYAML only when regenerating from the pinned upstream GameIndex. The
emulator reads the generated INI and never needs Python, a network, or ROM paths.
"""
import argparse
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
    parser.add_argument('gameindex', type=Path)
    args = parser.parse_args()
    import yaml
    seed = json.loads((ROOT / 'catalogue-seed.json').read_text(encoding='utf-8'))
    raw = args.gameindex.read_bytes().replace(b'\r\n', b'\n')
    if hashlib.sha256(raw).hexdigest() != seed['upstream_gameindex_sha256']:
        raise ValueError('Use the pinned upstream GameIndex; changed data requires review.')
    games, identities = generate(seed, yaml.safe_load(raw))
    (ROOT / 'catalogue.json').write_text(json.dumps({**seed, 'games': games}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    ini = '; Automatic Sorting Titles 0.1.0-test1; generated from catalogue.json\n; Manual overrides belong in inis/sorting-titles.ini, not this file.\n\n'
    ini += ''.join(f'[{serial}]\nSortingTitle = {title}\n\n' for serial, title in sorted(identities.items()))
    (ROOT / 'automatic-sorting.ini').write_text(ini, encoding='utf-8', newline='\n')
    print(f'{len(games)} curated games, {len(identities)} explicit serial identities; remaining titles retain normal ordering.')


if __name__ == '__main__':
    main()
