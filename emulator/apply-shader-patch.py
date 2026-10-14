"""Apply the prototype only to the two pinned, clean source trees."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent


def edit(path, before, after, count=1):
    text = path.read_text(encoding='utf-8-sig')
    if text.count(before) != count:
        raise RuntimeError(f'Unexpected source in {path.name}: {before[:70]!r}')
    path.write_text(text.replace(before, after), encoding='utf-8', newline='\n')


def main(pcsx2, sg):
    # Hash all original touched files before modifying anything.
    expected = json.loads((ROOT / 'upstream-shader-hashes.json').read_text())
    for name, digest in expected.items():
        tree, relative = name.split('/', 1)
        path = (pcsx2 if tree == 'pcsx2' else sg) / relative
        if hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest() != digest:
            raise RuntimeError('Unexpected upstream content: ' + name)
    shutil.copy2(ROOT / 'patch/ShaderPrototype.h', pcsx2 / 'pcsx2-qt/ShaderPrototype.h')
    mainwindow = pcsx2 / 'pcsx2-qt/MainWindow.cpp'
    edit(mainwindow, '#include "MainWindow.h"', '#include "MainWindow.h"\n#include "ShaderPrototype.h"')
    # At this point the surface has a container but has not been shown or handed
    # to the GS. Hook before either fullscreen or ordinary show paths.
    anchor = '#ifdef __APPLE__\n\tif (!render_to_main && (fullscreen || g_emu_thread->isExclusiveFullscreen()))'
    edit(mainwindow, anchor,
         '#ifdef _WIN32\n\tif (s_vm_valid && !ShaderPrototype::Attach(m_display_surface, [] { g_emu_thread->setVMPaused(true); })) return;\n#endif\n\n' + anchor)
    edit(mainwindow, '\tcreateDisplayWidget(fullscreen, render_to_main);',
         '\tcreateDisplayWidget(fullscreen, render_to_main);\n'
         '#ifdef _WIN32\n\tif (s_vm_valid && !ShaderPrototype::HasGate()) { destroyDisplayWidget(true); return std::nullopt; }\n#endif')
    edit(mainwindow, 'void MainWindow::destroyDisplayWidget(bool show_game_list)\n{',
         'void MainWindow::destroyDisplayWidget(bool show_game_list)\n{\n#ifdef _WIN32\n\tShaderPrototype::Detach();\n#endif')
    edit(mainwindow, 'void MainWindow::onVMStopped()\n{',
         'void MainWindow::onVMStopped()\n{\n#ifdef _WIN32\n\tShaderPrototype::Detach();\n#endif')
    # A fullscreen library can reuse its render surface when a VM starts.
    edit(mainwindow, 'void MainWindow::onVMStarting()\n{\n\ts_vm_valid = true;',
         'void MainWindow::onVMStarting()\n{\n\ts_vm_valid = true;\n#ifdef _WIN32\n\tif (m_display_surface) ShaderPrototype::Attach(m_display_surface, [] { g_emu_thread->setVMPaused(true); });\n#endif')
    display = pcsx2 / 'pcsx2-qt/DisplayWidget.cpp'
    edit(display, '#include "DisplayWidget.h"', '#include "DisplayWidget.h"\n#include "ShaderPrototype.h"')
    edit(display, 'void DisplaySurface::updateCursor(bool hidden)\n{',
         'void DisplaySurface::updateCursor(bool hidden)\n{\n#ifdef _WIN32\n\tShaderPrototype::Cursor(hidden);\n#endif')
    qt = pcsx2 / 'pcsx2-qt/QtHost.cpp'
    edit(qt, '#include "QtHost.h"', '#include "QtHost.h"\n#include "ShaderPrototype.h"')
    edit(qt, 'm_is_exclusive_fullscreen = m_is_fullscreen && GSWantsExclusiveFullscreen();',
         'm_is_exclusive_fullscreen = m_is_fullscreen && GSWantsExclusiveFullscreen();\n'
         '\tif (ShaderPrototype::Enabled() && m_is_exclusive_fullscreen)\n'
         '\t{\n#ifdef _WIN32\n\t\tShaderPrototype::Log("Exclusive fullscreen unsupported: select borderless fullscreen in the test copy.");\n#endif\n'
         '\t\treturn std::nullopt;\n\t}')
    edit(qt, 'const bool render_to_main = !m_is_exclusive_fullscreen && !window_fullscreen && m_is_rendering_to_main;',
         'const bool render_to_main = !m_is_exclusive_fullscreen && !window_fullscreen && m_is_rendering_to_main && !ShaderPrototype::Enabled();')
    sd = sg / 'ShaderGlass'
    shutil.copy2(ROOT / 'patch/WorkerMain.cpp', sd / 'WinMain.cpp')
    shutil.copy2(ROOT / 'patch/PrototypeReady.h', sd / 'PrototypeReady.h')
    edit(sd / 'CaptureManager.cpp', '#include "CaptureManager.h"',
         '#include "CaptureManager.h"\n#include "PrototypeReady.h"')
    edit(sd / 'CaptureManager.cpp',
         'MessageBox(m_options.outputWindow, error.message().c_str(), L"ShaderGlass", MB_OK | MB_ICONERROR);',
         'OutputDebugStringW(error.message().c_str()); // No worker UI.')
    edit(sd / 'CaptureManager.cpp', 'CreateEvent(NULL, FALSE, FALSE, L"FrameEvent")',
         'CreateEvent(NULL, FALSE, FALSE, NULL)')
    edit(sd / 'CaptureManager.cpp', '        ProcessFrame();',
         '        try { ProcessFrame(); }\n'
         '        catch (const winrt::hresult_error& e) { PrototypeLog("Render HRESULT " + std::to_string(e.code().value) + ": " + winrt::to_string(e.message())); ExitProcess(23); }\n'
         '        catch (const std::exception& e) { PrototypeLog(e.what()); ExitProcess(23); }\n'
         '        catch (...) { PrototypeLog("Unknown render exception"); ExitProcess(23); }')
    edit(sd / 'ShaderGlass.h', 'void PresentFrame();', 'void PresentFrame(bool filtered = false);')
    edit(sd / 'ShaderGlass.cpp', '#include "ShaderGlass.h"',
         '#include "ShaderGlass.h"\n#include "PrototypeReady.h"')
    edit(sd / 'ShaderGlass.cpp', 'void ShaderGlass::PresentFrame()\n{',
         'void ShaderGlass::PresentFrame(bool filtered)\n{\n    HRESULT presented;')
    edit(sd / 'ShaderGlass.cpp', 'm_swapChain->Present1(0, presentFlags, &presentParameters);',
         'presented = m_swapChain->Present1(0, presentFlags, &presentParameters);')
    edit(sd / 'ShaderGlass.cpp', 'm_swapChain->Present(0, presentFlags);',
         'presented = m_swapChain->Present(0, presentFlags);')
    edit(sd / 'ShaderGlass.cpp', '    PostMessage(m_outputWindow, WM_PAINT, 0, 0); // necessary for click-through',
         '    winrt::check_hresult(presented);\n'
         '    if (filtered && prototypeReady && (presented == S_OK || presented == DXGI_STATUS_OCCLUDED))\n'
         '    {\n'
         '        // The opaque output remains above the source when the startup cover\n'
         '        // opens. An occluded swapchain can then present its filtered buffer.\n'
         '        winrt::check_hresult(DwmFlush());\n'
         '        static bool logged = false;\n'
         '        if (!logged) { PrototypeLog(presented == S_OK ? "first filtered Present: S_OK" : "first filtered Present: occluded; opaque output retained"); logged = true; }\n'
         '        SetEvent(prototypeReady);\n    }')
    edit(sd / 'ShaderGlass.cpp', '    PresentFrame();\n\n    m_renderCounter++;',
         '    PresentFrame(true);\n\n    m_renderCounter++;')
    # Fail through the bridge on DXGI/D3D errors rather than release-build null access.
    s = sd / 'ShaderGlass.cpp'
    text = s.read_text()
    text = text.replace('assert(SUCCEEDED(hr));', 'winrt::check_hresult(hr);')
    # Initialise the output to black even on early presentation paths.
    anchor = '    m_device->CreateRenderTargetView(m_displayTexture.get(), 0, m_displayRenderTarget.put());'
    if text.count(anchor) != 1: raise RuntimeError('Unexpected render target creation')
    text = text.replace(anchor,
        '    winrt::check_hresult(m_device->CreateRenderTargetView(m_displayTexture.get(), 0, m_displayRenderTarget.put()));\n'
        '    m_context->ClearRenderTargetView(m_displayRenderTarget.get(), background_colour);')
    s.write_text(text, encoding='utf-8', newline='\n')
    # No shader/menu/browser/dialog code is linked into this entry point.
    project = sd / 'ShaderGlass.vcxproj'
    for filename in ['BrowserWindow.cpp', 'CompileWindow.cpp', 'CropDialog.cpp',
                     'HotkeyDialog.cpp', 'InputDialog.cpp', 'ParamsWindow.cpp', 'ShaderWindow.cpp']:
        edit(project, f'    <ClCompile Include="{filename}" />\n', '')
    edit(project, '/await /Zc:twoPhase- /Gw ', '/await /Zc:twoPhase- /bigobj /Gw ')
    print('Applied isolated ShaderGlass prototype patch.')


if __name__ == '__main__':
    main(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
