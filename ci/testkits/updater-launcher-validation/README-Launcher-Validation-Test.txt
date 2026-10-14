PCSX2 Controlled Updater 0.3.0 - launcher validation test1

PURPOSE
This is a separate updater test. The accepted updater, custom launcher and
emulator binaries are not overwritten. The published release/feed stay unchanged.
The test updater uses the same selected-runtime state as the normal updater in
YOUR TEST COPY. Installing/rolling back through it changes that copy's selection.

SETUP
1. Close PCSX2 and the updater. Use a separate full copy of your accepted custom
   nightly installation named exactly PCSX2-Nightly-Test. Your existing test copy
   is suitable if it still contains the working launcher and updater.
2. Extract this ZIP directly into that copy's root, beside Custom-PCSX2.exe.
   It adds Test-PCSX2-Update.cmd and one separate test folder. It must not ask to
   replace Custom-PCSX2.exe, PCSX2-Update.exe or the normal updater scripts.
3. Run Test-PCSX2-Update.cmd. For these checks, use this file instead of the normal
   PCSX2-Update.exe. The title must say 0.3.0 - launcher validation test1.

CHECK 1 - ACCEPTED LAUNCHER
Expect 'Launcher: compatible (accepted Custom-PCSX2.exe)'. The selected custom
version and rollback target should be readable (for example PCSX2 2.9.127 and
PCSX2 2.9.126). These labels describe the selected build, not a running process.
The original pcsx2-qt.exe is separate and is deliberately not updated.

CHECK 2 - MISSING LAUNCHER
Close PCSX2 and the test updater. With file name extensions visible, temporarily
rename Custom-PCSX2.exe to Custom-PCSX2.exe.test-backup in THIS TEST COPY ONLY.
Reopen Test-PCSX2-Update.cmd. Expect a launcher-validation message with repair
instructions. Download and install, Install local ZIP, and Roll back must be
disabled. Check for updates should still work. No runtime selection changes.
Close the test updater and rename the file back to Custom-PCSX2.exe. Reopen the
test updater; compatibility should be restored.
If the EXE was already missing or was the old launcher, the bundled
PCSX2-Updater-Launcher-Repair-test1.zip contains the exact previously accepted
replacement. Back up an existing EXE before extracting that repair at the root.

CHECK 3 - UPDATE AND ROLLBACK
Using the TEST updater, switch to 2.9.126 with Roll back if currently on 2.9.127.
Launch Custom-PCSX2.exe and confirm the displayed version, then close it.
Use Check for updates -> Download and install to select the approved 2.9.127.
Launch Custom-PCSX2.exe, confirm 2.9.127, and launch a game. Close PCSX2, roll back
through the TEST updater, and confirm Custom-PCSX2.exe starts the previous version.
If you already have a different previous runtime, report that version rather
than assuming it is 2.9.126. Keep official PCSX2 automatic updates disabled.

WHAT IS CHECKED
The entire launcher must match the accepted SHA-256:
4fab61885b8aa0fa413255b5d1927d6a785ef52e99e68203dc52d08828f147f9
Missing, unreadable, changed and unrecognised launchers block state changes.
A differently rebuilt launcher is not automatically trusted; its hash must be
reviewed and added explicitly. The updater never runs unknown EXEs to test them.
The engine checks again after downloads and holds the verified EXE open against
replacement while it installs or rolls back. Existing package signatures,
hashes, dependency checks, settings backups and runtime locks remain in use.
This is a compatibility check, not a malware scanner or Authenticode signature.

REMOVAL
Close the test updater. Restore the launcher filename if you renamed it. Remove
Test-PCSX2-Update.cmd, this README, and the folder
custom-pcsx2/updater-launcher-validation-test1.
The normal PCSX2-Update.exe continues using its original scripts. Runtime
selection is whichever version you last selected in this test copy; removal
does not automatically roll it back. The separate working installation is intact.

Please report whether all three checks passed, preferably with screenshots of
the compatible and missing-launcher states. Do not promote this updater to your
working installation yet.
