# Custom PCSX2

Unofficial custom PCSX2 builds and a controlled updater. Not affiliated with the PCSX2 project.

The current approved runtime is based on PCSX2 nightly **2.9.127**, upstream commit `e35cb2c87590bc3d127b3bb4dd222b01e598c9a4`. See the [approved release](https://github.com/AMT-Hub/pcsx2-custom/releases/tag/nightly-2.9.127-ci1-test1). The earlier approved 2.9.126 releases remain available.

Custom emulator features include compatibility-aware regional BIOS selection, integrated ShaderGlass worker coordination, editable sorting titles for every game, and disabled official updates. The updater accepts signed custom packages, preserves portable user data, and retains a previous runtime for rollback.

## Scope

Release packages are **runtime updates for an existing matching custom installation**, not standalone PCSX2 installations. They require the expected ShaderGlass worker/profile and custom launcher. BIOS firmware and game images are not included. Existing controller profiles and game settings remain in the user's portable data folder.

The 2.9.127 runtime passed user acceptance of the custom features, game launch, signed installation through PCSX2-Update.exe, rollback to 2.9.126 and game launch after rollback on 14 October 2026. See [the acceptance record](ci/acceptance/2026-10-14-2.9.127-candidate1.json). The exact tested package is published with signed feed revision 3. Compilation, signatures and these acceptance tests do not prove compatibility across all games and GPUs.

## Launcher requirement

Keep the updater-compatible `Custom-PCSX2.exe` in each custom nightly installation. An EXE restored from a pre-updater portable ZIP can ignore the selected runtime and continue launching the old version. The accepted launcher has SHA-256 `4fab61885b8aa0fa413255b5d1927d6a785ef52e99e68203dc52d08828f147f9`.

If an installation still has that older launcher, close PCSX2 and the updater, back up its existing EXE, then extract `PCSX2-Updater-Launcher-Repair-test1.zip` from the approved release into that installation. The repair contains the unchanged updater-compatible launcher and does not change BIOS files, settings or runtimes. Restoring it resolved the reported selected/launched version mismatch; subsequent game and rollback tests passed. The updater does not yet enforce launcher compatibility automatically.

## Feed

Configure the custom updater with:

`https://github.com/AMT-Hub/pcsx2-custom/releases/latest/download/approved-feed.json`

The feed and packages are signed with the project release key. The public verification key is in `updater/public-key.xml`. The signing key is never distributed here. Optional automatic checks run when the updater opens; installation requires user action. Local installation and rollback remain available. Leave official PCSX2 automatic updates disabled.

## Source

- `emulator/`: exact feature patches, pinned upstream commit and Windows build process. Public packaging produces an unsigned runtime without needing personal data.
- `launcher/`: native custom launcher and updater wrapper source.
- `updater/`: PowerShell installation engine, feed transport/verification and UI.
- `publisher/`: package and feed signing tools; supply your own private key outside the repository.

See `emulator/README.md` for prerequisites and build instructions. Rebuilding does not automatically approve or sign a release. Reusing a release ID for different bytes is unsupported.

PCSX2-derived code retains GPLv3 terms and upstream notices; see COPYING.GPLv3. ShaderGlass patch material retains its licence in emulator/ShaderGlass-LICENSE. Third-party dependencies retain their respective licences. This repository does not change upstream copyright or licensing notices.
