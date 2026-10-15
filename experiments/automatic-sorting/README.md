# Automatic Sorting Titles — rules catalogue 0.2.0-test1

Experimental catalogue update for BOTH existing Automatic Sorting Titles
0.1.0-test1 test installations: stable PCSX2 2.8.2 and custom nightly 2.9.127.
The accepted builds, launchers, signed update feed and runtime EXEs are unchanged.

## Install

1. Close PCSX2. Use the separate test copy in which Automatic Sorting Titles
   already works. This small update does not install the missing EXE feature.
2. Extract `PCSX2-Automatic-Sorting-Rules-0.2.0-test1-update.zip` beside that
   copy's `Custom-PCSX2.exe`, merging `custom-pcsx2` and replacing the one
   `resources/automatic-sorting.ini` file when asked.
3. Launch `Custom-PCSX2.exe`. The same procedure applies to stable and nightly.
   Keep the nightly test copy's existing `legacy` selection. Do not run the
   controlled updater to install this unsigned experiment.
4. Open Game Properties > Summary > Sorting Title. If you previously edited
   or cleared a title, right-click its field > **Use automatic sorting title**
   only when you want to discard that override and inspect the new default.

The EXE tooltip still says Automatic Sorting Titles test1: only its data changed.
The catalogue header identifies version 0.2.0-test1. The catalogue loads once at
process start, so restart after installing it. No Python or Internet is needed.
First-time prototype installation is documented in `README-0.1.0-test1.md`.

## What changed

The original 50-game seed was too narrow. General rules now process the entire
pinned PS2 identity database, independently of the user's installed collection.
The runtime consumes their compiled serial-to-title results through the existing
scanner. Adding a game directory, rescanning, and cached startup use this same
lookup. Adding/removing installed games cannot renumber the rest of a series.

Rules apply in this order, followed by the runtime's manual override:

- Normalise recognised whole Roman numeral tokens; protect ambiguous letters
  and known names such as Guilty Gear XX, Mega Man X and Hunter X Hunter.
- Resolve metadata aliases for stylised titles (Driv3r), regional names and
  consistent franchise prefixes. Do not globally replace digits inside words.
- Detect unnumbered first games from numbered siblings across the whole database.
  A unique subtitled first game is also supported. Years do not count as sequels.
- Generate PS2 release-order positions for configured franchise families; apply
  developer grouping (publisher fallback) where that policy is selected.
- Infer further subtitle families only with shared-region identity evidence,
  complete dates, no competing numbered series and an unambiguous date order.
- Apply the user's explicit preferences and semantic exceptions, including
  Secret Agent Clank / Ratchet, The Hobbit / LOTR, Team ICO and the screenshot.

God of War / II become 1 / 2 through general numbering rules. Crash's six PS2
games receive 1–6 from release metadata. GTA keeps III at 3 and receives 3.1–3.4
for Vice City, San Andreas, Liberty City Stories and Vice City Stories.
These positions are sorting preferences, not official franchise numbers.

## Scope and honest limits

See `RULES-COVERAGE.json` for exact counts and unresolved candidate families.
The output covers over 11,000 eligible disc identities, including regional
editions and reissues; this is NOT 11,000 separate games or verified chronologies.
Most defaults remain normal titles. Whole-token normalisation is broader than
franchise/release-order coverage. Missing dates, developer conflicts, unresolved
regional equivalence and ambiguous chronology do not receive invented positions.

Rules alone cannot discover that Secret Agent Clank belongs beside Ratchet,
or decide the preferred placement of movie adaptations. Those relationships
remain metadata. The repository can expand that metadata and regenerate defaults
without hand-writing each output title, rebuilding the EXE, or scanning your ROMs.
A game added later that has a known serial works immediately. An identity absent
from the catalogue retains normal PCSX2 title ordering and an editable field;
this version does not perform runtime Roman conversion on unknown serials.

`COLLECTION-COVERAGE.md` audits all 114 supplied collection entries against stock
database identities. Filenames do not prove the actual serial/CRC of your ROMs;
undubs and other modified discs need runtime confirmation. Demo filtering is
conservative and does not prove that every remaining entry is a retail game.
The original Quidditch=Harry Potter 4 preference is retained. Later Harry Potter
numbering still needs a policy resolving that conflict with Goblet of Fire.

## Manual edits and rollback

Defaults never enter `inis/sorting-titles.ini`. Existing manual values always
win and remain intact across scans and catalogue updates. Clearing a field opts
that identity out; right-click > Use automatic sorting title resets the override.
Displayed game names and ROM filenames do not change.

To roll back the catalogue: close PCSX2, then copy
`custom-pcsx2/automatic-sorting-0.2.0-test1/rollback/automatic-sorting.ini` over
`custom-pcsx2/shader-prototype/resources/automatic-sorting.ini`, and restart.
That is the original 0.1.0-test1 catalogue. Your manual edits remain unchanged.
To roll back the entire prototype, use the untouched accepted installation or
follow the saved nightly active.txt instructions in README-0.1.0-test1.md.

## Test this update

- Check God of War 1 / 2, Ratchet & Clank 6, Driver 3, GTA 3–3.4, Crash 1–6
  and Lord of the Rings 0.5 - The Hobbit in ascending title order.
- Add another folder with a game outside the original screenshot, such as
  Devil May Cry or a later Burnout / Crash game. It should receive its generated
  default after the ordinary scan, without running any external tool.
- Edit one value, restart and rescan; confirm the edit survives. Check clearing
  and restoring automatic mode. Other custom functionality should still work.

Automated rules, precedence and packaging tests do not replace Windows acceptance.
Do not promote this catalogue into accepted builds until the user accepts it.

## Reproduce and maintain

`rules.py` is the general compiler; `rules.json` contains policies, aliases and
release facts; `catalogue-seed.json` retains explicit user exceptions.
`identity-metadata.json.gz` is a compact facts-only, hash-pinned snapshot of
PCSX2 GameIndex plus title-checked date/developer/publisher records from Libretro.
No game descriptions, BIOS files, ROM files or personal settings are included.
Provenance, rejected joins and input hashes are in METADATA-PROVENANCE.json.
Facts are not all independently historically verified; see RESEARCH.md.

From the repository root:

```sh
python3 experiments/automatic-sorting/generate_catalogue.py
python3 experiments/automatic-sorting/audit_collection.py --input /path/to/private-list.tsv --output /path/to/private-audit
python3 -m unittest discover -s experiments/automatic-sorting/tests -v
g++ -std=c++17 experiments/automatic-sorting/tests/policy.cpp -o /tmp/sorting-policy
/tmp/sorting-policy
python3 experiments/automatic-sorting/package_catalogue.py --output /tmp/PCSX2-Automatic-Sorting-Rules-0.2.0-test1-update.zip
```

Regeneration from the checked-in snapshot needs only the Python standard library.
Rebuilding the facts snapshot with prepare_metadata.py additionally needs PyYAML
and the exact pinned input files. Metadata or rule changes are reviewed and tested
before a new catalogue is distributed. Source follows the repository's licence.

Personal collection lists and audit outputs are excluded from the public source
repository. The personal download can include its audit via package_catalogue.py
--private-report-dir; a public package omits it.
