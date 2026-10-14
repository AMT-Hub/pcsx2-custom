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

This candidate pipeline automates assessment and the reviewed build. It does not automatically port arbitrary nightlies, approve gameplay, sign packages, create releases or refresh feed expiry. The existing updater remains unchanged and only sees separately signed/published approved releases. No secrets or write permission are requested by the candidate workflow.

## Daily discovery and reporting

The separate **[Discover official PCSX2 nightlies](https://github.com/AMT-Hub/pcsx2-custom/actions/workflows/nightly-discovery.yml)** workflow checks official published prereleases daily at **06:23 UTC** (06:23 UK winter time / 07:23 UK summer time). Use **Run workflow** on `main` for an immediate check. GitHub schedules can be delayed and public-repository schedules may be disabled after 60 days without repository activity; the Actions page is the source of truth for the latest successful check. See [GitHub's schedule documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

Read the persistent **[discovery report index](https://github.com/AMT-Hub/pcsx2-custom/tree/nightly-discovery-reports)**. Each candidate report has Markdown and JSON versions under `reports/`, retained in that separate branch's history. Daily run summaries and 30-day diagnostic artifacts show successful no-change checks, failures and any backlog. No issues, comments or email notifications are generated by the script. GitHub's own notification settings still apply to workflow failures.

Discovery:

- Scans release pages through the reviewed version, includes the full boundary page, and sorts valid nightly version tags numerically. Stable releases, drafts and non-version tags are excluded. It never uses `/releases/latest`, which excludes prereleases. A 2,000-release scan limit fails visibly rather than silently claiming complete coverage.
- Resolves the upstream tag to its exact commit and verifies that the reviewed baseline tag still matches our pinned commit.
- Checks all 13 integration files against the existing reviewed hashes, reads the wider upstream file comparison, and highlights BIOS/boot, graphics/fullscreen/pause UI, sorting, controller input, settings/launch and build/dependency paths. These are review hints, not a semantic analysis or compatibility guarantee.
- Notes whether the expected Windows archive exists, without downloading or trusting it. Missing archives, changed ancestry and potentially truncated comparisons are reported. GitHub comparison responses cap their changed-file list at 300; at that boundary the report explicitly requires a full local comparison.
- Deduplicates by tag, resolved commit, release asset metadata and the current review/discovery inputs. Retagged candidates, changed assets and changed baseline/policy inputs produce a fresh record. Closed or expired artifacts are not used as persistent state. At most 10 unseen candidates are assessed per run, newest first; additional candidates are reported as a backlog and processed on subsequent runs.
- Reads upstream source as bytes at the resolved commit. It does not check out, import, patch, compile or execute upstream source. Every newly discovered candidate has `build_permitted: false` and `release_approved: false`, even when all 13 hashes match.

The reporting job uses the repository's built-in `GITHUB_TOKEN` with `contents: write` solely to commit reports and state to `nightly-discovery-reports`. No PAT, signing key or new secret is required. Tests, pull requests and feature-branch checks have read-only permissions. The report branch starts with no source-code parent; updates preserve its existing tree and reject concurrent non-fast-forward changes. It never updates `main`, reviewed emulator pins, runtime releases or the signed approved feed.

To pause daily discovery, disable this workflow in GitHub Actions. Existing reports remain available and approved updates continue to work. To resume, enable it and run it manually. To change the daily time, edit the workflow's UTC cron expression.

For local read-only checking, run `python ci/discover_nightlies.py`. `GH_TOKEN` is optional for public reads but recommended to avoid GitHub's anonymous rate limit. Only `--publish` writes the dedicated report branch. Keep generated output outside tracked source (`discovery-output/` is ignored).
