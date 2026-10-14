#define UNICODE
#define _UNICODE
#include <windows.h>
#include <filesystem>
#include <string>
int WINAPI wWinMain(HINSTANCE,HINSTANCE,PWSTR,int) {
 wchar_t path[32768], sys[32768];
 DWORD n=GetModuleFileNameW(nullptr,path,32768); if(!n||n>=32768)return 1;
 auto root=std::filesystem::path(std::wstring(path,n)).parent_path();
 GetSystemDirectoryW(sys,32768);
 auto exe=std::filesystem::path(sys)/L"WindowsPowerShell/v1.0/powershell.exe";
 auto script=root/L"custom-pcsx2/updater/Updater.ps1";
 if(!std::filesystem::exists(script)){MessageBoxW(nullptr,L"Extract the entire updater component into your custom PCSX2 folder.",L"PCSX2 Updater",MB_ICONERROR);return 1;}
 std::wstring cmd=L"\""+exe.wstring()+L"\" -NoLogo -NoProfile -STA -ExecutionPolicy Bypass -File \""+script.wstring()+L"\"";
 STARTUPINFOW si{};si.cb=sizeof(si); PROCESS_INFORMATION pi{};
 if(!CreateProcessW(exe.c_str(),cmd.data(),nullptr,nullptr,FALSE,CREATE_NO_WINDOW,nullptr,root.c_str(),&si,&pi)){MessageBoxW(nullptr,L"Could not start Windows PowerShell.",L"PCSX2 Updater",MB_ICONERROR);return 1;}
 CloseHandle(pi.hThread); WaitForSingleObject(pi.hProcess,INFINITE);DWORD code=0;GetExitCodeProcess(pi.hProcess,&code);CloseHandle(pi.hProcess);return int(code);
}
