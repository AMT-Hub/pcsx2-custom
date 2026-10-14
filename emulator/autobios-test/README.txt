PCSX2 Auto BIOS - Windows build kit 3
====================================

This is the build step, not the finished component installer.
The source patch and selection-policy tests have been checked here. A complete
Windows compile and actual game launches have not yet been verified.

WHAT TO DO
If updating kit 1 or 2: extract over the existing build-kit folder, replace files
when prompted, and retain the work folder. Then run Build.cmd again.

1. Extract this entire ZIP into a short writable folder such as D:\PCSX2Build.
   Do not extract into your PCSX2 installation. Avoid parentheses in the path.
2. Double-click Build.cmd. No administrator rights or Visual Studio UI needed.
3. Leave the window open while it downloads and compiles.
4. If it succeeds, send PCSX2-AutoBIOS-Build.zip and Build.log from this folder.
   If it stops, send Build.log. If no log appears, send the window's text.

The script is tailored to your detected Visual Studio 2022 C++ toolchain and
Python 3.13 launcher. It locates CMake, Ninja, Git and 7-Zip automatically.
The first run downloads PCSX2 source plus approximately 208 MB of dependencies.
Allow several GB for the extracted dependencies, source and compiler outputs.
It can be rerun after an interrupted compile; completed build steps are reused.
Do not manually edit the source in work while using this kit.

All source, dependencies and compiler output live under this folder. It does
not install tools system-wide, edit your current PCSX2 installation, copy your
BIOS or games, or change the accepted Xbox component. Keep this folder until
the component has passed testing and we have archived its code and build.

BUILD DETAILS
- Kit 3 prefers Visual Studio's CMake and checks for cmcldeps.exe, the helper
  missing from the failed resource compiler command. If the bundled tools are
  unavailable, it downloads a SHA-256 verified official portable CMake 3.31.6
  into work/tools. No system-wide tool installation or PATH changes are made.
  It builds a tiny resource file first, then regenerates the existing emulator
  build rules with the explicit helper path and resumes the build.
- Kit 2 captures Git error messages. If Git specifically reports dubious
  ownership, it trusts only this build checkout for the build process and its
  child processes. Your global Git settings are not changed. Other Git errors
  stop the build and appear in Build.log. Source origin and commit are checked.
- Official PCSX2 v2.8.2 commit:
  fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3
- Uses your Visual Studio 2022 compiler with CMake/Ninja in Release mode.
- Uses the official prebuilt Windows dependencies, pinned by SHA-256.
  This package is newer than v2.8.2's minimum dependencies; the first full
  Windows compile is still needed to establish compatibility.
- Uses FFmpeg 8 runtime libraries expected by this PCSX2 release.
- Disables the custom build's updater so official updates cannot replace it.
- Creates a separate PCSX2-AutoBIOS.exe and a portable test-build archive.
  Taskbar pinning and the component installer remain to be validated/packaged.
- The downloaded dependency URL is mutable. If its bytes change, this script
  stops instead of silently changing dependencies. Send the resulting log.

AUTO BIOS BEHAVIOUR TO TEST AFTER BUILDING
- The hook runs before BIOS loading and NVRAM loading, during VM startup.
- Uses PCSX2's game-list region and native image readers, not filename guesses.
- Maps to Japan, USA, Europe, Asia or China retail BIOS families.
- Keeps the configured BIOS if it matches; otherwise chooses the newest
  recognised matching BIOS in the configured BIOS folder, with a stable tie-break.
- Falls back to the configured BIOS if region is unknown or no match exists.
- Does not rewrite the configured BIOS setting.
- The marker custom-pcsx2/auto-bios.enabled enables the feature.
- A missing/invalid configured fallback results in a BIOS error instead of
  silently picking an unrelated region.
- Bare ELF launches, PS1 discs, BIOS-only starts and unknown game regions use
  the configured BIOS. Native v2.8.2 disc-image support defines format coverage;
  this does not add a new CUE parser or additional emulator formats.

Do not replace your working installation with this untested build. Once it
compiles, we will package the component and test region switching, fallback,
BIOS sidecars, game-list launching and component removal before accepting it.

Source changes are under GPL-3.0-or-later. PCSX2 and its dependencies retain
their upstream licences. This kit contains no BIOS or game files.
