# Custom PCSX2 2.9.126 runtime source/build kit

Upstream commit: `a77a07903152617d81f0fbefc1c297fbcd26dac5` (tag v2.9.126).
https://github.com/PCSX2/pcsx2/tree/a77a07903152617d81f0fbefc1c297fbcd26dac5

This kit contains the feature patches and pinned build process used for the accepted runtime: compatibility-aware Auto BIOS, ShaderGlass integration, editable sorting titles, and disabling official automatic updates. Emulator feature patches are unchanged from the accepted build. The packaging step has been changed to produce only an unsigned runtime, without requiring a Personal portable archive.

On Windows, use Visual Studio 2022 Desktop development with C++, Python 3.13, Git and 7-Zip. Extract this directory to a short writable location. Download the official `pcsx2-v2.9.126-windows-x64-Qt.7z` from the PCSX2 v2.9.126 release and place it beside Build.cmd. Run Build.cmd. Upstream source and dependencies are downloaded and hash/commit checked. The output is `PCSX2-Nightly-2.9.126-runtime-UNSIGNED.zip`.

No BIOS images, game images, personal settings or signing key are required to compile. The policy tables contain BIOS identities and selection rules, not firmware bytes. The runtime is intended for a matching custom portable installation, with its separately installed ShaderGlass worker/profile and launcher. It is not standalone. Rebuilt binaries require testing and explicit package signing before the updater accepts them.

The complete Windows build of the accepted feature source was previously tested. This new public packaging path has been checked separately without rebuilding the emulator; byte-for-byte reproducibility across different compiler/runtime installations is not claimed. Historical validation files describe the original port.

PCSX2 licensing is preserved in COPYING.GPLv3 and upstream source notices. ShaderGlass patch material retains its upstream licence in ShaderGlass-LICENSE. Dependencies retain their own licences and source/build locations from the pinned upstream projects. Full upstream source is fetched at the exact commits named by build.py; feature modifications are all included here.
