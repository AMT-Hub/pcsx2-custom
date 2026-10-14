#ifndef UNICODE
#define UNICODE
#endif
#define _UNICODE
#define _WIN32_WINNT 0x0601
#include <windows.h>
#include <shobjidl.h>
#include <propkey.h>
#include <propvarutil.h>
#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <string>
#include <vector>
#include <set>
namespace fs = std::filesystem;
static DWORD childPid;
static HICON smallIcon=nullptr, largeIcon=nullptr;
static std::wstring relaunch, icon, displayName;
static std::set<HWND> configured;
static std::wstring quote(const std::wstring& s) {
  std::wstring out=L"\""; unsigned slashes=0;
  for(wchar_t c:s) { if(c==L'\\'){++slashes;continue;} if(c==L'\"')out.append(slashes*2+1,L'\\');else out.append(slashes,L'\\');slashes=0;out+=c; }
  out.append(slashes*2,L'\\'); return out+L"\"";
}
static HRESULT set(IPropertyStore* store, REFPROPERTYKEY key, const std::wstring& text) {
  PROPVARIANT v; PropVariantInit(&v); HRESULT hr=InitPropVariantFromString(text.c_str(),&v);
  if(SUCCEEDED(hr))hr=store->SetValue(key,v);
  PropVariantClear(&v);return hr;
}
static BOOL CALLBACK identify(HWND window,LPARAM) {
  DWORD pid=0;GetWindowThreadProcessId(window,&pid);
  if(pid!=childPid || !IsWindowVisible(window) || GetWindow(window,GW_OWNER) || configured.count(window))return TRUE;
  DWORD_PTR ignored=0;
  if(smallIcon) SendMessageTimeoutW(window,WM_SETICON,ICON_SMALL,reinterpret_cast<LPARAM>(smallIcon),SMTO_ABORTIFHUNG,100,&ignored);
  if(largeIcon) SendMessageTimeoutW(window,WM_SETICON,ICON_BIG,reinterpret_cast<LPARAM>(largeIcon),SMTO_ABORTIFHUNG,100,&ignored);
  IPropertyStore* store=nullptr;
  if(SUCCEEDED(SHGetPropertyStoreForWindow(window,IID_PPV_ARGS(&store)))) {
    bool ok=SUCCEEDED(set(store,PKEY_AppUserModel_RelaunchCommand,relaunch));
    ok=SUCCEEDED(set(store,PKEY_AppUserModel_RelaunchDisplayNameResource,displayName))&&ok;
    ok=SUCCEEDED(set(store,PKEY_AppUserModel_RelaunchIconResource,icon))&&ok;
    ok=SUCCEEDED(set(store,PKEY_AppUserModel_ID,L"CustomPCSX2.Portable"))&&ok;
    if(SUCCEEDED(store->Commit())&&ok)configured.insert(window);
    store->Release();
  }
  return TRUE;
}
int WINAPI wWinMain(HINSTANCE instance,HINSTANCE,PWSTR args,int) {
  smallIcon=static_cast<HICON>(LoadImageW(instance,MAKEINTRESOURCEW(101),IMAGE_ICON,GetSystemMetrics(SM_CXSMICON),GetSystemMetrics(SM_CYSMICON),LR_DEFAULTCOLOR));
  largeIcon=static_cast<HICON>(LoadImageW(instance,MAKEINTRESOURCEW(101),IMAGE_ICON,GetSystemMetrics(SM_CXICON),GetSystemMetrics(SM_CYICON),LR_DEFAULTCOLOR));
  CoInitializeEx(nullptr,COINIT_APARTMENTTHREADED);
  std::vector<wchar_t> buffer(32768);DWORD n=GetModuleFileNameW(nullptr,buffer.data(),DWORD(buffer.size()));
  fs::path self(std::wstring(buffer.data(),n)),root=self.parent_path();
  // Portable all-in-one release: the accepted combined runtime implements both components.
  const fs::path runtime=root/L"custom-pcsx2"/L"shader-prototype";
  const fs::path exe=runtime/L"PCSX2-ShaderPrototype.exe";
  if(!fs::exists(exe) || !fs::exists(root/L"ShaderGlass"/L"ShaderGlass-PCSX2.exe")){
    MessageBoxW(nullptr,L"The portable package is incomplete. Extract the entire PCSX2 folder from the ZIP before launching.",L"Custom PCSX2",MB_ICONERROR);return 1;
  }
  try{
    const auto marker=runtime/L"custom-pcsx2"/L"auto-bios.enabled";
    fs::create_directories(marker.parent_path());
    if(!fs::exists(marker)){
      std::ofstream f(marker); if(!f)throw std::runtime_error("Cannot enable Auto BIOS");
    }
  }catch(...){MessageBoxW(nullptr,L"Cannot enable Auto BIOS. Extract PCSX2 to a writable folder.",L"Custom PCSX2",MB_ICONERROR);return 1;}
  SetEnvironmentVariableW(L"PCSX2_SHADER_PROTOTYPE_ROOT",root.c_str());
  SetCurrentProcessExplicitAppUserModelID(L"CustomPCSX2.Portable");
  relaunch=quote(self.wstring());icon=self.wstring()+L",-101";displayName=L"@"+self.wstring()+L",-101";
  // runtime/portable.txt points two directories up to the shared install root.
  std::wstring cmd=quote(exe.wstring())+L" "+args;
  STARTUPINFOW si{};si.cb=sizeof(si);PROCESS_INFORMATION pi{};
  if(!CreateProcessW(exe.c_str(),cmd.data(),nullptr,nullptr,FALSE,0,nullptr,root.c_str(),&si,&pi)){
    std::wstring message=L"Could not start Custom PCSX2. Windows error "+std::to_wstring(GetLastError());
    MessageBoxW(nullptr,message.c_str(),L"Custom PCSX2",MB_ICONERROR);return 1;
  }
  CloseHandle(pi.hThread);childPid=pi.dwProcessId;
  while(WaitForSingleObject(pi.hProcess,100)==WAIT_TIMEOUT){
    for(auto it=configured.begin();it!=configured.end();)if(!IsWindow(*it))it=configured.erase(it);else ++it;
    EnumWindows(identify,0);
  }
  DWORD code=0;GetExitCodeProcess(pi.hProcess,&code);CloseHandle(pi.hProcess);CoUninitialize();return int(code);
}
