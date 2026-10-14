# Custom PCSX2

Unofficial custom PCSX2 builds and a controlled updater. Not affiliated with the PCSX2 project.

The first approved runtime is based on PCSX2 nightly **2.9.126**, upstream commit `a77a07903152617d81f0fbefc1c297fbcd26dac5`.

Custom emulator features include compatibility-aware regional BIOS selection, integrated ShaderGlass worker coordination, editable sorting titles for every game, and disabled official updates. The updater accepts signed custom packages, preserves portable user data, and retains a previous runtime for rollback.

## Scope

Release packages are **runtime updates for an existing matching custom installation**, not standalone PCSX2 installations. They require the expected ShaderGlass worker/profile and custom launcher. BIOS firmware and game images are not included. Existing controller profiles and game settings remain in the user's portable data folder.

The 2.9.126 runtime and 0.2.0 online-feed updater passed user acceptance, including update and rollback. See ci/acceptance/2026-10-14-ci1.json for the accepted GitHub build. This branch prepares a separate 2.9.127 candidate; it does not change the approved release or feed. Compilation and signatures alone do not prove compatibility across all games and GPUs.

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
