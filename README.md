# Custom PCSX2

Unofficial custom PCSX2 builds and a controlled updater. Not affiliated with the PCSX2 project.

The current approved runtime is based on PCSX2 nightly **2.9.127**, upstream commit `e35cb2c87590bc3d127b3bb4dd222b01e598c9a4`. See the [approved release](https://github.com/AMT-Hub/pcsx2-custom/releases/tag/nightly-2.9.127-ci1-test1). The earlier approved 2.9.126 releases remain available.

Custom emulator features include compatibility-aware regional BIOS selection, integrated ShaderGlass worker coordination, editable sorting titles for every game, and disabled official updates. The updater accepts signed custom packages, preserves portable user data, and retains a previous runtime for rollback.

## Scope

Release packages are **runtime updates for an existing matching custom installation**, not standalone PCSX2 installations. They require the expected ShaderGlass worker/profile and custom launcher. BIOS firmware and game images are not included. Existing controller profiles and game settings remain in the user's portable data folder.

The 2.9.127 runtime passed user acceptance of the custom features, game launch, signed installation through PCSX2-Update.exe, rollback to 2.9.126 and game launch after rollback on 14 October 2026. See [the acceptance record](ci/acceptance/2026-10-14-2.9.127-candidate1.json). The exact tested package is published with signed feed revision 3. Compilation, signatures and these acceptance tests do not prove compatibility across all games and GPUs.

## Launcher requirement

Keep the updater-compatible `Custom-PCSX2.exe` in each custom nightly installation. An EXE restored from a pre-updater portable ZIP can ignore the selected runtime and continue launching the old version. The accepted launcher has SHA-256 `4fab61885b8aa0fa413255b5d1927d6a785ef52e99e68203dc52d08828f147f9`.

If an installation still has that older launcher, close PCSX2 and the updater, back up its existing EXE, then extract `PCSX2-Updater-Launcher-Repair-test1.zip` from the approved release into that installation. The repair contains the unchanged updater-compatible launcher and does not change BIOS files, settings or runtimes. Restoring it resolved the reported selected/launched version mismatch; subsequent game and rollback tests passed. Updater **0.3.0** now enforces launcher compatibility before online/local installation and rollback. It checks the accepted launcher bytes again after download and prevents replacement while the runtime selection changes. Read-only feed checks remain available when the launcher is incompatible. The UI displays the selected custom version and rollback target.

The 0.3.0 launcher-validation component passed 38 automated Windows PowerShell 5.1 checks and the user's UI, update, rollback and intervening launch checks. See [its acceptance record](ci/acceptance/2026-10-14-updater-launcher-validation-test1.json). To adopt it in an existing matching custom nightly installation, close PCSX2/the updater, back up `custom-pcsx2/updater`, and extract `PCSX2-Updater-0.3.0-Accepted-Overlay.zip` at the installation root. Then use the normal `PCSX2-Update.exe`. This one-time overlay updates only the updater scripts; the runtime feed still selects custom 2.9.127. The old stable 0.8.0 Personal build is outside this overlay's scope.

## Feed

Configure the custom updater with:

`https://github.com/AMT-Hub/pcsx2-custom/releases/latest/download/approved-feed.json`

The feed and packages are signed with the project release key. The public verification key is in `updater/public-key.xml`. The signing key is never distributed here. Optional automatic checks run when the updater opens; installation requires user action. Local installation and rollback remain available. Leave official PCSX2 automatic updates disabled.

## Nightly discovery

The [discovery workflow](https://github.com/AMT-Hub/pcsx2-custom/actions/workflows/nightly-discovery.yml) checks official nightlies hourly at **:53 UTC** and records source compatibility assessments in a [separate report branch](https://github.com/AMT-Hub/pcsx2-custom/tree/nightly-discovery-reports). Its index shows the last successful check and last successful scheduled check separately; manual or push runs do not establish that scheduling works. New candidates remain review-required; matching file hashes do not approve an update. It does not build, sign or publish candidates. See [discovery and review instructions](ci/README.md#automatic-discovery-and-reporting).

## Source

- `emulator/`: exact feature patches, pinned upstream commit and Windows build process. Public packaging produces an unsigned runtime without needing personal data.
- `launcher/`: native custom launcher and updater wrapper source.
- `updater/`: PowerShell installation engine, feed transport/verification and UI.
- `publisher/`: package and feed signing tools; supply your own private key outside the repository.

See `emulator/README.md` for prerequisites and build instructions. Rebuilding does not automatically approve or sign a release. Reusing a release ID for different bytes is unsupported.

PCSX2-derived code retains GPLv3 terms and upstream notices; see COPYING.GPLv3. ShaderGlass patch material retains its licence in emulator/ShaderGlass-LICENSE. Third-party dependencies retain their respective licences. This repository does not change upstream copyright or licensing notices.
