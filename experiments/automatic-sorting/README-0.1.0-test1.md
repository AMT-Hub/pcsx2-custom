# Automatic Sorting Titles 0.1.0-test1

Experimental component for the accepted stable PCSX2 2.8.2 / Portable 0.8.0
Personal installation and custom nightly 2.9.127. This is not an approved
replacement for either working build. Use a separate copy of the whole PCSX2
folder for testing; keep the accepted original intact.

## What this first prototype covers

- The 50 games in the user's 15 October 2026 screenshot, represented by 271
  explicitly identified regional/reissue serials. `catalogue.json` lists every
  mapped serial and the corresponding upstream names and regions.
- Every detected game has a visible editable Sorting Title field. Reviewed
  games receive the curated default; unmatched games use PCSX2's existing title
  sorting, displayed in that field. A field value does not imply curated coverage.
- Fresh scans, cached startup and adding game directories use the same lookup.
  There is no separate ROM crawler, filename matching, Internet lookup or
  per-game setting to configure. Formats supported by PCSX2's game scanner
  follow its normal identity extraction; this does not add archive-format support.
- Numeric title sorting: `7, 10, 10.1, 10.2, 11, 12, 12.1`, without changing the
  displayed game names. Roman-numeral conversion is currently explicit catalogue
  data, not a global text replacement (which could corrupt names such as Ico).

This is a seed catalogue, not a claim to cover every PS2 release or every regional
edition. The rest of the user's collection and wider major franchises still need
research and review. Demo/beta/compilation entries are not guessed into retail
series. English names from the pinned PCSX2 database help identify Japanese and
other regional releases, but unreviewed aliases remain unmatched.

## Install the matching overlay in a TEST COPY

Close PCSX2 and the updater first. Do not extract either overlay over your only
working installation. Run `Custom-PCSX2.exe`, not the official `pcsx2-qt.exe`.

### Stable

Extract `PCSX2-Automatic-Sorting-stable-0.1.0-test1-overlay.zip` at the root of a
separate copy of PCSX2-Portable-0.8.0-Personal. This replaces only the nested
custom emulator EXE, adds its catalogue, and adds build/test information.
Then launch the copy's existing Custom-PCSX2.exe. Discard the test copy to revert.

### Nightly

Extract `PCSX2-Automatic-Sorting-nightly-0.1.0-test1-overlay.zip` at the root of a
separate copy of the accepted custom nightly installation. This uses the
launcher's existing manual/legacy runtime path in the test copy. It replaces
that copy's nested legacy runtime, keeping its installed signed runtime folders
and launcher intact. Your original installation must remain separate.

In the TEST COPY, save a copy of `custom-pcsx2/updater/active.txt`, then replace
its contents with this one line:

```
legacy
```

Launch the existing Custom-PCSX2.exe. To return to the signed 2.9.127 runtime,
close it and restore the saved active.txt (provided it selected the signed runtime
before this test). Otherwise discard the test copy. Do not use the controlled
updater to assess this unsigned prototype: its fixed legacy label may say 2.9.126.
Use the emulator's About information and the Sorting Title tooltip instead.
The signed feed is unchanged. No release manifest/signature or approval is
fabricated to make an unsigned build look like an approved updater runtime.

## Manual control and persistence

Properties > Summary > Sorting Title remains visible and editable for every
listed game. The tooltip identifies this component as Automatic Sorting Titles
test1, which also helps distinguish the custom executable from the official one.

Edit the value and press Tab to save. Your value always takes precedence. Clear
the field to opt that game out of automatic sorting and use normal database/title
ordering. Right-click inside the field and choose **Use automatic sorting title**
to remove that override and return to the catalogue default.

Automatic values are read from the active runtime's
`resources/automatic-sorting.ini`. Manual values remain in the existing portable
`inis/sorting-titles.ini`. Scanning never writes defaults into this file. Existing
non-empty manual entries need no migration and are never replaced by catalogue
updates. Explicit clearing uses `UseNormalTitle=true`; older builds ignore this
extra key and already have no automatic catalogue to apply.

Manual disc identities use the accepted serial+CRC key, preserving edits when
the ROM or portable install moves. Identical disc identities share edits. Different
revisions/patches with different CRCs retain independent overrides. Entries with
no reliable serial+CRC retain the accepted encoded-path fallback, so moving those
unidentified files can require another edit. CRC-specific catalogue entries are
supported before serial-wide defaults, although the seed uses serials only.

Catalogue changes take effect after restarting the emulator. Returning to the
signed nightly runtime selects its own resources while keeping manual settings.

## Catalogue policy and unresolved scope

The screenshot's literal sorting titles are the starting authority, not factual
claims about official franchise membership. For example, The Clone Wars is
deliberately grouped as Battlefront 0.5; the engine does not infer that relationship.
Numbering is stable across installed collections: adding/removing a game does not
renumber another game. Preserve franchise numbering when explicitly requested
(Spyro 4/5, Final Fantasy 7/10/11/12), even where earlier games were not on PS2.

Regional aliases resolve to the same reviewed title, but title text alone is not
an identity. US Gadget Racers (`SLUS-20225`) maps to Choro Q HG 1; EU Gadget Racers
(`SLES-51911`) maps to Choro Q HG 3. Deadlocked and Gladiator both map to Ratchet
& Clank 4. No assumption about identical names is made at runtime.

Harry Potter Quidditch World Cup remains **Harry Potter 4**, exactly as supplied.
A comprehensive catalogue must resolve its conflict with the later main-series
PS2 games Goblet of Fire, Order of the Phoenix and Half-Blood Prince. No answer
was received to the optional full-catalogue numbering question, so this prototype
does not silently change the explicit screenshot preference to 7. Those later
games retain ordinary title ordering for now.

Expansion policy: use reviewed franchise/series grouping first, instalment or
agreed story order second, then earliest PS2 release date within an agreed
developer/publisher group for otherwise unordered games. Developer and publisher
are separate fields, not interchangeable. Record exact evidence and a rationale
for each proposed grouping; dates alone cannot establish the user's preferred
order. Do not derive this from filenames or download a live unreviewed catalogue.

Identity evidence is the pinned PCSX2 GameIndex:
https://github.com/PCSX2/pcsx2/blob/e35cb2c87590bc3d127b3bb4dd222b01e598c9a4/bin/resources/GameIndex.yaml

Additional primary research:
- Insomniac's original Ratchet series list: https://insomniac.games/game/ratchet-and-clank/
- EA confirms Half-Blood Prince's PS2 release and identifies Order of the Phoenix:
  https://news.ea.com/press-releases/press-releases-details/2009/EA-and-Warner-Bros.-Interactive-Entertainment-Confirm-Harry-Potter-and-the-Half-Blood-Prince-Video-Game-Release-Date/default.aspx

## Acceptance checks

1. Confirm the tooltip says Automatic Sorting Titles test1. Check TimeSplitters,
   Jak, Ratchet, Final Fantasy, Team ICO and both Choro Q region cases. Use title
   sorting in ascending list and grid views; display names must remain unchanged.
2. Edit one automatic value and restart. Rescan all games and confirm the edit
   survives. Existing manual entries from the accepted build must also survive.
3. Clear a value, restart/rescan and confirm it stays opted out. Right-click the
   field > Use automatic sorting title and confirm the catalogue value returns.
4. Add another ROM directory containing a mapped game. Its automatic title must
   appear after the normal PCSX2 scan, without restarting or rerunning a tool.
5. Confirm an unmatched title remains sensibly ordered and editable. Rename/move
   a recognised ROM and confirm its serial+CRC manual override still applies.
6. Launch games and check controller pause hotkey, Auto BIOS, ShaderGlass in
   Vulkan fullscreen/windowed and cursor behaviour through the pause menu.
7. Nightly: restore the saved active.txt and confirm the previously accepted
   custom runtime launches. Stable: return to the untouched original installation.

Source application and policy/catalogue tests do not prove Windows GUI or game
behaviour. Windows build and user acceptance results must be recorded separately
before integrating this component into the accepted stable or nightly builds.

## Source and build

All changes are isolated under this experiment and its dedicated test workflow.
Accepted emulator build scripts, updater scripts, launcher, discovery schedule,
signing configuration and approved feed are unchanged. `prepare_build.py` creates
disposable copies of the accepted build kit with version-specific input hashes.
No BIOS files, ROMs or personal settings are needed or included.

The catalogue is reproducible from `catalogue-seed.json` and the hash-pinned
GameIndex with `generate_catalogue.py` (PyYAML required for this development step
only). `catalogue.json` preserves the resolved identities for review; the INI is
the offline runtime payload. Source code follows the repository's GPL licence.
