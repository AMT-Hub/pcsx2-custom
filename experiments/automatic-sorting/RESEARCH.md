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
PCSX2 identity and corroborating release records. Version 0.2.0 ships a compact facts-only snapshot after title validation.
Descriptions are excluded. 3,098 fact records pass the join; 1,446 candidate
records are rejected and listed in METADATA-PROVENANCE.json. Passing the join
does not independently verify the historical accuracy of a date or studio.

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


## 0.2.0 implementation and additional evidence

The general compiler now processes all 12,841 pinned identities, excluding 1,383
known demo/trial/non-retail entries. Coverage and unresolved candidates are
reported separately. Newly installed known identities use the already-generated
catalogue; no installed-game list is an input to generation.

Publisher evidence distinguishes PS2 port dates from original PSP dates. Liberty
City Stories reached PS2 in 2006 and Vice City Stories in 2007; their relative
order is unchanged. Reviewed family chronology uses years where years suffice,
without inventing exact days. Equal/overlapping date precision cannot establish
a unique order. Release chronology is a sorting policy, not story chronology.

Selected corroborating sources examined:

- Secret Agent Clank's PS2 release and relationship: https://blog.playstation.com/2009/03/16/secret-agent-clank-coming-to-ps2/comment-page-2/
- Vice City launch: https://ir.take2games.com/static-files/63b50ea9-bc60-4cc8-9cb6-1b7a3718507b
- Liberty City Stories on PS2: https://ir.take2games.com/static-files/8c71a1b4-4142-4d54-830a-b5a10f46f300
- Vice City Stories on PS2: https://ir.take2games.com/static-files/744c1b53-72cc-4587-8f90-4abb644a230d
- Official God of War series overview: https://www.playstation.com/en-us/god-of-war/
- Crash: Mind Over Mutant launch: https://investor.activision.com/static-files/f365e97c-db41-44ab-9f4d-3a11b2fc8a8e
- Crash release overview (secondary): https://en.wikipedia.org/wiki/List_of_Crash_Bandicoot_video_games
- Burnout series overview (secondary): https://en.wikipedia.org/wiki/Burnout_%28series%29
- Simpsons release overview (secondary): https://en.wikipedia.org/wiki/List_of_The_Simpsons_video_games
- Medal of Honor: Frontline PS2 date (secondary): https://en.wikipedia.org/wiki/Medal_of_Honor%3A_Frontline
- WipEout Pulse PS2 port date (secondary): https://gamefaqs.gamespot.com/ps2/960820-wipeout-pulse

These references support selected family decisions; they are not a claim that
every inferred family or imported fact has been independently checked. Broad
identity coverage must never be presented as comprehensive chronology research.
Inferred subtitle families are conservative candidates; unknown regional
relationships, mixed numbered/subtitle families, date gaps and studio conflicts
are reported. Manual preferences always take precedence.

No new Windows executable was compiled for 0.2.0 because scanner integration,
manual override handling and sorting comparison code are unchanged. The original
prototype was reported working by the user, with catalogue omissions. This data
revision still needs their Windows acceptance; it is not promoted to main or to
the accepted stable/nightly feed.
