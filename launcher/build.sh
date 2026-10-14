#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
windres="${WINDRES:-x86_64-w64-mingw32-windres}"
cxx="${CXX:-x86_64-w64-mingw32-g++}"
"$windres" --preprocessor="$cxx" --preprocessor-arg=-E --preprocessor-arg=-xc --preprocessor-arg=-DRC_INVOKED -I . launcher.rc -o launcher.o
"$cxx" -std=c++17 -O2 -Wall -Wextra -static -municode -mwindows launcher.cpp launcher.o -o Custom-PCSX2.exe -lole32 -luuid -lshell32 -lpropsys -lshlwapi -luser32
"$cxx" -std=c++17 -O2 -Wall -Wextra -static -municode -mwindows updater.cpp launcher.o -o PCSX2-Update.exe -luser32
