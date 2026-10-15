# Custom PCSX2 2.9.127 runtime source/build kit

Upstream commit: `e35cb2c87590bc3d127b3bb4dd222b01e598c9a4` (tag v2.9.127).
https://github.com/PCSX2/pcsx2/tree/e35cb2c87590bc3d127b3bb4dd222b01e598c9a4

This kit contains the feature patches and pinned build process for the 2.9.127 candidate: compatibility-aware Auto BIOS, ShaderGlass integration, automatic sorting defaults with editable overrides, and disabling official automatic updates. Automatic Sorting Titles 0.2.0 was accepted on 15 October 2026; its source remains in `../experiments/automatic-sorting` to preserve the tested source paths. The packaging step has been changed to produce only an unsigned runtime, without requiring a Personal portable archive.

On Windows, use Visual Studio 2022 Desktop development with C++, Python 3.13, Git and 7-Zip. Clone or extract the full repository to a short writable location, retaining `experiments/automatic-sorting`, and open this directory. For a standalone kit, run `python experiments/automatic-sorting/prepare_build.py nightly <new-directory>` from the repository root. Download the official `pcsx2-v2.9.127-windows-x64-Qt.7z` from the PCSX2 v2.9.127 release and place it beside Build.cmd. Run Build.cmd. Upstream source and dependencies are downloaded and hash/commit checked. The output is `PCSX2-Nightly-2.9.127-runtime-UNSIGNED.zip`.

No BIOS images, game images, personal settings or signing key are required to compile. The policy tables contain BIOS identities and selection rules, not firmware bytes. The runtime is intended for a matching custom portable installation, with its separately installed ShaderGlass worker/profile and launcher. It is not standalone. Rebuilt binaries require testing and explicit package signing before the updater accepts them.

The previous 2.9.126 runtime passed Windows feature, update and rollback acceptance. The 2.9.127 source review is recorded in ../ci/reviews/2.9.127.json. This candidate still requires a fresh Windows build and acceptance; no gameplay approval is implied by source checks. Byte-for-byte reproducibility across compiler installations is not claimed.

PCSX2 licensing is preserved in COPYING.GPLv3 and upstream source notices. ShaderGlass patch material retains its upstream licence in ShaderGlass-LICENSE. Dependencies retain their own licences and source/build locations from the pinned upstream projects. Full upstream source is fetched at the exact commits named by build.py; feature modifications are all included here.
