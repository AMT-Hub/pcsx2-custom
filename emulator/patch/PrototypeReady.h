#pragma once
#include <filesystem>
// Shared only within the worker. Set after a successfully presented filtered frame.
inline HANDLE prototypeReady = nullptr;
inline std::wstring prototypeLogPath;
inline void PrototypeLog(const std::string& message)
{
    if (prototypeLogPath.empty()) return;
    const HANDLE file = CreateFileW(prototypeLogPath.c_str(), FILE_APPEND_DATA,
        FILE_SHARE_READ | FILE_SHARE_WRITE, nullptr, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (file == INVALID_HANDLE_VALUE) return;
    const std::string line = message + "\r\n";
    DWORD written = 0;
    WriteFile(file, line.data(), static_cast<DWORD>(line.size()), &written, nullptr);
    CloseHandle(file);
}
