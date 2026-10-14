// Controlled PCSX2 prototype entry point. GPL-3.0-or-later.
// Uses ShaderGlass 1.3.0's capture and shader engine, without its UI.
#include "pch.h"
#include "CaptureManager.h"
#include "Helpers.h"
#include "PrototypeReady.h"
#include <filesystem>
#include <map>
#include <stdexcept>

static void LoadProfile(CaptureManager& manager, const wchar_t* path)
{
    std::ifstream input{std::filesystem::path(path)};
    if (!input) throw std::runtime_error("Profile cannot be opened");
    std::map<std::string, std::string> values;
    std::string key, value;
    while (input >> key >> std::quoted(value)) values[key] = value;
    if (values.at("ProfileVersion") != "1.1") throw std::runtime_error("Unsupported profile version");
    auto& o = manager.m_options;
    o.pixelWidth = o.pixelHeight = std::stof(values.at("PixelSize"));
    o.aspectRatio = std::stof(values.at("AspectRatio"));
    o.frameSkip = std::stoul(values.at("FrameSkip"));
    o.dpiScale = 1.0f;
    if (values.at("DPIScaling") != "0" || values.at("OutputScale") != "Free")
        throw std::runtime_error("Prototype expects supplied profile scaling");
    o.freeScale = true;
    o.outputScale = 1;
    o.flipHorizontal = values.at("FlipH") == "1";
    o.flipVertical = values.at("FlipV") == "1";
    o.vertical = values.at("Vertical") == "1";
    o.clone = values.at("Clone") == "1";
    o.transparent = true;
    o.captureCursor = false; // Native PCSX2 cursor is authoritative.
    if (values.at("InputArea") != "0 0 0 0" || values.at("CroppedArea") != "0 0 0 0")
        throw std::runtime_error("Prototype expects uncropped supplied profile");
    bool found = false;
    for (unsigned i = 0; i < manager.Presets().size(); ++i)
    {
        const auto& p = manager.Presets()[i];
        if (p->Category == values.at("ShaderCategory") && p->Name == values.at("ShaderName"))
        { o.presetNo = i; found = true; break; }
    }
    if (!found || o.presetNo == 0) throw std::runtime_error("Required built-in preset not found");
    std::vector<std::tuple<int, std::string, double>> params;
    for (const auto& [k, v] : values)
    {
        if (k.rfind("Param-", 0) != 0) continue;
        const auto dash = k.find('-', 6);
        if (dash == std::string::npos) throw std::runtime_error("Invalid shader parameter");
        params.emplace_back(std::stoi(k.substr(6, dash - 6)), k.substr(dash + 1), std::stod(v));
    }
    manager.SetParams(params);
}

int APIENTRY wWinMain(HINSTANCE instance, HINSTANCE, LPWSTR, int)
{
    SetErrorMode(SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX | SEM_NOOPENFILEERRORBOX);
    SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
    try
    {
        int argc = 0;
        auto argv = CommandLineToArgvW(GetCommandLineW(), &argc);
        if (!argv || argc != 8) return 10;
        prototypeLogPath = argv[7];
        const DWORD pid = std::stoul(argv[1]);
        const HWND source = reinterpret_cast<HWND>(std::stoull(argv[2]));
        const HWND output = reinterpret_cast<HWND>(std::stoull(argv[3]));
        DWORD sourcePid = 0, outputPid = 0;
        GetWindowThreadProcessId(source, &sourcePid);
        GetWindowThreadProcessId(output, &outputPid);
        if (!IsWindow(source) || !IsWindow(output) || sourcePid != pid || outputPid != pid) return 11;
        HANDLE parent = OpenProcess(SYNCHRONIZE, FALSE, pid);
        HANDLE stop = OpenEventW(SYNCHRONIZE, FALSE, argv[5]);
        prototypeReady = OpenEventW(EVENT_MODIFY_STATE, FALSE, argv[4]);
        if (!parent || !stop || !prototypeReady) return 12;
        std::ofstream log{std::filesystem::path(argv[7]), std::ios::app};
        log << "worker started pid=" << GetCurrentProcessId() << " source=" << source << " output=" << output << std::endl;
        winrt::init_apartment(winrt::apartment_type::multi_threaded);
        CaptureLib::Disable();
        if (!HasCaptureAPI()) return 13;
        // Lifetime is exactly this process. ExitProcess avoids upstream's unjoined
        // render-thread teardown; the OS reclaims all capture and graphics objects.
        auto manager = new CaptureManager(instance);
        manager->Initialize();
        LoadProfile(*manager, argv[6]);
        manager->m_options.captureWindow = source;
        manager->m_options.outputWindow = output;
        if (!manager->StartSession()) return 14;
        log << "capture started; waiting for filtered presentation" << std::endl;
        HANDLE handles[] = {parent, stop};
        while (WaitForMultipleObjects(2, handles, FALSE, 100) == WAIT_TIMEOUT)
        {
            if (!IsWindow(source) || !IsWindow(output)) break;
        }
        log << "worker stopped" << std::endl;
        ExitProcess(0);
    }
    catch (const winrt::hresult_error& error)
    { PrototypeLog("HRESULT " + std::to_string(error.code().value) + ": " + winrt::to_string(error.message())); return 20; }
    catch (const std::exception& error) { PrototypeLog(error.what()); return 21; }
    catch (...) { PrototypeLog("Unknown worker exception"); return 22; }
    return 0;
}
