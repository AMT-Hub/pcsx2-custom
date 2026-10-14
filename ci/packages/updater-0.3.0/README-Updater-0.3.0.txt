PCSX2 Controlled Updater 0.3.0 - accepted launcher validation

INSTALL INTO YOUR EXISTING CUSTOM NIGHTLY INSTALLATION
1. Close PCSX2 and every updater window.
2. Back up the existing custom-pcsx2/updater folder to a separate location.
3. Extract this ZIP into your custom nightly installation root, beside
   Custom-PCSX2.exe and PCSX2-Update.exe. Allow replacement of Engine.ps1,
   Feed.ps1 and Updater.ps1 inside custom-pcsx2/updater.
4. Open your normal PCSX2-Update.exe. Its window should say
   PCSX2 Controlled Updater 0.3.0 and report the accepted launcher as compatible.

Use PCSX2-Update.exe from now on. Test-PCSX2-Update.cmd is no longer needed.
Your existing updater EXE already opens these scripts, so no EXE replacement
or compiler is required. Keep the accepted Custom-PCSX2.exe in place.

WHAT CHANGED
Missing, unreadable or unrecognised custom launchers block downloads/installs
and rollback, with repair instructions. Checking the release feed still works.
The launcher is checked again after download and held open against replacement
while installation or rollback changes the selected runtime.
The window shows the selected custom emulator version and rollback target.
The original pcsx2-qt.exe remains separate and is not updated by this component.

This is an updater-only overlay for the existing matching custom NIGHTLY
installation, not the old stable 0.8.0 Personal build or a standalone emulator.
It does not contain or replace the launcher, emulator, BIOS files, settings,
controller profile, ShaderGlass files, public key, feed configuration, selected
runtime, memory cards or saves. Keep official PCSX2 automatic updates disabled.

ACCEPTANCE
All 38 Windows PowerShell 5.1 regression checks passed. The user confirmed
successful updates, rollback and intervening PCSX2 launches. Screenshots also
confirmed the compatible-launcher state and disabled state-changing buttons
when the launcher was missing.
The three scripts are the accepted test implementation. Only the window title
has changed to remove the test suffix; Engine.ps1 and Feed.ps1 are unchanged.
The approved emulator release/feed remain on custom 2.9.127.

REMOVE THE OLD SIDE-BY-SIDE TEST (OPTIONAL)
With the test updater closed, remove Test-PCSX2-Update.cmd,
README-Launcher-Validation-Test.txt and the separate folder
custom-pcsx2/updater-launcher-validation-test1.
Do not remove custom-pcsx2/updater or custom-pcsx2/runtimes.

REVERT THIS COMPONENT IF NEEDED
Close all updater/PCSX2 windows. Restore Engine.ps1, Feed.ps1 and Updater.ps1
from your backup to custom-pcsx2/updater. Restoring scripts does not change the
selected emulator version, current settings or saved games.

Source and acceptance records: https://github.com/AMT-Hub/pcsx2-custom
The PowerShell files in this package are the complete source of this overlay.
