Native launcher and updater wrapper source

launcher.cpp selects the controlled runtime and retains the taskbar identity/icon, game arguments and ShaderGlass environment. updater.cpp runs the PowerShell UI. launcher-original.cpp is the pre-updater reference.
Build Windows x64 helpers using MinGW-w64: set CXX and WINDRES as required, then run bash build.sh from this directory. Deploy Custom-PCSX2.exe and PCSX2-Update.exe at the portable installation root. Updater scripts are in ../updater and must be installed at custom-pcsx2/updater.
The emulator build/patch source is in ../emulator. Existing accepted launcher binaries are not changed by the feed overlay.
The PCSX2 icon and derived resources retain upstream licensing/notices. No private signing key or personal data is included.
