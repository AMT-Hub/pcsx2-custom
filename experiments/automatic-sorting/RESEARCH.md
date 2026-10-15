# Catalogue research notes — 15 October 2026

## Identity and preferred order are separate

PCSX2's pinned GameIndex has 12,841 records, including regions, reissues, demos
and non-retail entries. These are not 12,841 different retail games. Its serial
lookup and English/localised names are the identity base for this prototype.
The user's screenshot supplies the 50 initial preferred orders. Runtime matching
uses explicit serials (optionally CRCs), never fuzzy filenames.

The manual Sorting Title patch still exists in both the recovered accepted
stable kit and repository nightly source. This does not establish why the user's
installed field disappeared. The official executable has a conditional read-only
database sorting-name field; the custom patch makes it universally editable.
The test tooltip and BUILD-INFO.json distinguish this prototype from either.

## Broader metadata candidate

Libretro's repository contains a PS2 metadata file with developer, publisher and
region-specific year/month/day values joined by serial. Although it sits under
`metadat/developer`, the other attributes are in the same file. It can help
prepare candidates for review, rather than individually researching every title
from scratch.

- Repository: https://github.com/libretro/libretro-database
- Pinned commit examined: `12c21cf79f1e20eff6ac68b80875816c717d0a7a`
- File: `metadat/developer/Sony - PlayStation 2.dat`
- SHA-256: `9f05f6938058d86b66cf3ee54d3b0b157f681c6fc14fb9bacb417edd68cd4b09`
- 4,726 records, 4,720 distinct serial strings; header version `2020.3.19`.
- It attributes its source to `robloach/libretro-database-psxdatacenter`.

Do not bulk-approve these rows. Inspection found serial collisions, including
Airforce Delta Strike and Airblade both assigned `SLUS-20346`, and Bujingai and
Bully both assigned `SLPS-25879`. Some duplicates are editions/discs, while others
conflict on title or date. Distinguish these cases explicitly against the pinned
PCSX2 identity and corroborating release records. No descriptions or metadata
from this candidate file are shipped in the prototype catalogue.

## Expansion workflow

1. Join external metadata by a validated serial, retaining source commit/URL and
   region. Reject collisions and missing/uncertain identities into a review list.
2. Group regional editions into one game and separate remakes, revisions,
   expansions, compilations and unrelated same-name releases.
3. Prefer explicit series numbering or the user's chosen story order. Preserve
   recognised franchise numbers where the user does so, even across PS2 gaps.
4. For otherwise unordered titles, propose developer/subseries groups inside the
   franchise, then use earliest PS2 release date within each group. Record how
   publisher changes and co-development were handled; a publisher is not a studio.
5. Keep subjective exceptions explicit (Team ICO, Clone Wars/Battlefront, LOTR).
   This is a preference catalogue, not an assertion of official series membership.
6. Review complete franchise proposals before shipping them. Do not renumber
   based on which games happen to be installed. Newly discovered titles use the
   same fixed defaults; existing manual edits still win.
7. Regenerate the serial catalogue deterministically, reject duplicate mappings,
   run policy checks and distribute it with a versioned test/approved runtime.

The initial prototype deliberately preserves all supplied screenshot values.
Harry Potter's later PS2 main games remain outside the curated seed until the
Quidditch=4 conflict is resolved. They still have editable normal Sorting Titles.
Unknown games remain normal defaults, clearly separate from researched coverage.

## Validation boundaries

The source patch applied to the relevant stable 2.8.2 and nightly 2.9.127 files.
Eight catalogue tests and the compiled C++ precedence/numeric-order checks passed
locally and on GitHub's Linux runner. Full Windows builds and the user's GUI,
folder-scan, persistence, shader/BIOS/controller checks are separate acceptance.

The first stable build attempt stopped before compilation because an unnecessary
official archive download differed from a historical local file. The corrected
stable preparation uses the recovered accepted source-only build bootstrap. It
does not consume that prebuilt archive, replace dependencies or patches.zip, or
change their checks. Source/dependency hash verification remains enabled.
