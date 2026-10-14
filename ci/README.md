# Reviewed nightly candidate pipeline

The approved 2.9.127 runtime completed the reviewed build, custom-feature tests and signed updater install/game/rollback/game acceptance on 14 October 2026. It is published unchanged with signed approved feed revision 3; see [the acceptance record](acceptance/2026-10-14-2.9.127-candidate1.json). Earlier 2.9.126 releases remain available. Running this pipeline alone never changes the live feed.

The 2.9.127 acceptance exposed an older `Custom-PCSX2.exe` launching the legacy runtime despite the updater selection. Restoring the previously supplied updater-compatible launcher resolved the mismatch. Keep that launcher in each nightly installation and verify both the displayed version and an actual game launch after updating and rolling back. The cause of the earlier EXE disappearance remains unconfirmed; do not assume that a restored EXE is updater-compatible.

## Use

In GitHub Actions, run **Assess and build custom nightly candidate**, entering the selected official tag. The reviewed baseline and default are `v2.9.127`; a newer tag must pass a separate source review before it can build. The workflow also retains its original push trigger for `candidate-nightly-2.9.127`. Neither a dispatch nor a branch push approves anything for the live feed.

The assessment records the exact upstream commit and compares all 13 reviewed integration files with their stored hashes. New tags/commits are marked **review-required**, even if those files match: dependency changes or changes elsewhere can still affect behaviour. No unreviewed upstream code is compiled or executed. An assessment job can succeed while correctly reporting review-required; the Windows build is then skipped.

Only the exact reviewed tag/commit proceeds to a Windows 2022 runner with Python 3.13 and Visual Studio 2022. It runs the existing source checks, feature patches, BIOS policy test and emulator build. Official archive/dependency downloads must match the pinned hashes. A changed moving dependency download stops the build; do not simply replace the expected hash to make it pass.

Download the assessment, build log and (on success) **UNSIGNED-runtime** artifact from the workflow run. Artifacts expire after 30 days. The ZIP is build output for separate acceptance/packaging, not an updater-installable package or a full portable installation. Never extract it over your working installation root.

## Approving a newer nightly

1. Assess the selected tag. Review its report and upstream changes.
2. Port patches and review source/build inputs in a separate branch. Update the pinned commit/tag, integration hashes, dependency hashes and packaging names together after review. The official download URL and runtime filename are derived from the pinned archive name to keep their versions consistent. The workflow default must still match the reviewed tag.
3. Build without a signing key. A green build is not proof of game, shader, cursor or taskbar compatibility.
4. Prepare an isolated test installation with the updater-compatible launcher, confirm the displayed emulator version after installation and rollback, and test region/BIOS selection (including fallback), ShaderGlass windowed/fullscreen/pause/shortcuts, controller hotkeys, sorting titles, launcher arguments/taskbar, update and rollback. Record exact artifact SHA-256 and results.
5. Sign accepted bytes using the offline publisher tools. Publish a new immutable runtime ID/tag/package and a higher-sequence signed feed, with corresponding source/licences. Keep unapproved candidates out of the approved feed.

This first pipeline automates assessment and the reviewed build. It does not automatically port arbitrary nightlies, approve gameplay, sign packages, create releases, schedule checks or refresh feed expiry. The existing updater remains unchanged and only sees separately signed/published approved releases. No secrets or write permission are requested by this workflow.
