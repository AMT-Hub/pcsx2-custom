// PCSX2 2.8.2 experimental ShaderGlass bridge. GPL-3.0-or-later.
#pragma once
#ifdef _WIN32
#include "common/RedtapeWindows.h"
#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QDateTime>
#include <QEvent>
#include <QPointer>
#include <QTimer>
#include <QWindow>
#include <functional>
#include <string>

namespace ShaderPrototype
{
inline QString Root() { return qEnvironmentVariable("PCSX2_SHADER_PROTOTYPE_ROOT"); }
inline bool Enabled() { return !Root().isEmpty(); }
inline void Log(const QString& text)
{
    QFile file(Root() + "/ShaderPrototype.log");
    if (file.open(QIODevice::WriteOnly | QIODevice::Append))
        file.write((QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs) + " " + text + "\n").toUtf8());
}

class Bridge final : public QObject
{
public:
    QPointer<QWindow> surface;
    HWND output = nullptr, cover = nullptr, capture = nullptr;
    HANDLE process = nullptr, ready = nullptr, stop = nullptr;
    QTimer timer;
    bool hiddenCursor = false, presented = false, failed = false;
    ULONGLONG began = 0;
    RECT previous{};
    std::function<void()> pause;

    Bridge() { connect(&timer, &QTimer::timeout, this, [this] { Tick(); }); }
    static LRESULT CALLBACK WindowProc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp)
    {
        auto self = reinterpret_cast<Bridge*>(GetWindowLongPtrW(hwnd, GWLP_USERDATA));
        if (msg == WM_NCCREATE)
        {
            self = static_cast<Bridge*>(reinterpret_cast<CREATESTRUCTW*>(lp)->lpCreateParams);
            SetWindowLongPtrW(hwnd, GWLP_USERDATA, reinterpret_cast<LONG_PTR>(self));
        }
        if (msg == WM_NCHITTEST) return HTTRANSPARENT;
        if (msg == WM_MOUSEACTIVATE) return MA_NOACTIVATE;
        if (msg == WM_SETCURSOR && self)
        {
            SetCursor(self->hiddenCursor ? nullptr : LoadCursorW(nullptr, IDC_ARROW));
            return TRUE;
        }
        if (msg == WM_ERASEBKGND) return TRUE;
        if (msg == WM_PAINT)
        {
            PAINTSTRUCT ps;
            HDC dc = BeginPaint(hwnd, &ps);
            // Never paint over the worker's presented swapchain.
            if (!self || hwnd == self->cover || !self->presented)
            {
                RECT r; GetClientRect(hwnd, &r);
                FillRect(dc, &r, static_cast<HBRUSH>(GetStockObject(BLACK_BRUSH)));
                if (self && self->failed)
                {
                    SetBkMode(dc, TRANSPARENT); SetTextColor(dc, RGB(255,255,255));
                    DrawTextW(dc, L"Shader prototype stopped. See ShaderPrototype.log.\nUse PCSX2 controls to stop the game.", -1, &r,
                        DT_CENTER | DT_VCENTER | DT_WORDBREAK);
                }
            }
            EndPaint(hwnd, &ps);
            return 0;
        }
        return DefWindowProcW(hwnd, msg, wp, lp);
    }
    void Close()
    {
        timer.stop();
        if (surface) surface->removeEventFilter(this);
        if (stop) SetEvent(stop);
        if (process)
        {
            // Allow normal worker exit. Do not block Qt while a graphics API might
            // send messages to its output HWND. Terminate only this owned worker.
            if (WaitForSingleObject(process, 0) == WAIT_TIMEOUT) TerminateProcess(process, 0);
            CloseHandle(process);
        }
        if (cover) DestroyWindow(cover);
        if (output) DestroyWindow(output);
        if (ready) CloseHandle(ready);
        if (stop) CloseHandle(stop);
        surface.clear(); output = cover = capture = nullptr;
        process = ready = stop = nullptr;
        presented = failed = false; previous = {}; pause = {};
    }
    void Fail(const QString& why)
    {
        if (failed) return;
        failed = true; presented = false;
        Log("FAIL: " + why);
        if (cover) { ShowWindow(cover, SW_SHOWNOACTIVATE); InvalidateRect(cover, nullptr, TRUE); }
        else if (surface) surface->hide();
        if (pause) pause();
    }
    bool Start(QWindow* window, std::function<void()> pauseVM)
    {
        if (!Enabled()) return true;
        if (surface == window) return output && cover;
        Close(); surface = window; pause = std::move(pauseVM);
        const HWND source = reinterpret_cast<HWND>(window->winId());
        capture = GetAncestor(source, GA_ROOT);
        WNDCLASSW wc{};
        wc.lpfnWndProc = WindowProc; wc.hInstance = GetModuleHandleW(nullptr);
        wc.lpszClassName = L"PCSX2ShaderPrototypeSurface";
        wc.hbrBackground = static_cast<HBRUSH>(GetStockObject(BLACK_BRUSH));
        if (!RegisterClassW(&wc) && GetLastError() != ERROR_CLASS_ALREADY_EXISTS)
            { Fail("Cannot register presentation window"); return false; }
        const DWORD ex = WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE | WS_EX_TRANSPARENT;
        output = CreateWindowExW(ex, wc.lpszClassName, L"", WS_POPUP, 0,0,1,1,
            capture, nullptr, wc.hInstance, this);
        cover = CreateWindowExW(ex, wc.lpszClassName, L"", WS_POPUP, 0,0,1,1,
            output, nullptr, wc.hInstance, this);
        if (!output || !cover) { Fail("Cannot create presentation gate"); return false; }
        window->installEventFilter(this);
        // Restrict event names to this session; no title-based window discovery.
        const auto token = QString("Local\\PCSX2Shader-%1-%2").arg(GetCurrentProcessId()).arg(GetTickCount64());
        const std::wstring readyName = (token + "-ready").toStdWString();
        const std::wstring stopName = (token + "-stop").toStdWString();
        ready = CreateEventW(nullptr, TRUE, FALSE, readyName.c_str());
        stop = CreateEventW(nullptr, TRUE, FALSE, stopName.c_str());
        began = GetTickCount64();
        Tick(); // Black gate exists before acquireRenderWindow returns to the GS.
        const QString worker = QDir::toNativeSeparators(Root() + "/ShaderGlass/ShaderGlass-PCSX2.exe");
        const QString profile = QDir::toNativeSeparators(Root() + "/ShaderGlass/Profiles/retro-crisis_1080p-curved_PS2.sgp");
        const QString log = QDir::toNativeSeparators(Root() + "/ShaderWorker.log");
        std::wstring command = (QString("\"%1\" %2 %3 %4 \"%5\" \"%6\" \"%7\" \"%8\"")
            .arg(worker).arg(GetCurrentProcessId()).arg(reinterpret_cast<quintptr>(capture))
            .arg(reinterpret_cast<quintptr>(output)).arg(QString::fromStdWString(readyName))
            .arg(QString::fromStdWString(stopName)).arg(profile).arg(log)).toStdWString();
        STARTUPINFOW si{}; si.cb = sizeof(si); PROCESS_INFORMATION pi{};
        const std::wstring cwd = QDir::toNativeSeparators(Root() + "/ShaderGlass").toStdWString();
        if (!ready || !stop || !CreateProcessW(worker.toStdWString().c_str(), command.data(), nullptr,
                nullptr, FALSE, CREATE_NO_WINDOW, nullptr, cwd.c_str(), &si, &pi))
            Fail(QString("Cannot start worker, Win32 error %1").arg(GetLastError()));
        else
        {
            process = pi.hProcess; CloseHandle(pi.hThread);
            Log(QString("gate created; capture=%1 output=%2 worker=%3")
                .arg(reinterpret_cast<quintptr>(capture)).arg(reinterpret_cast<quintptr>(output)).arg(pi.dwProcessId));
        }
        timer.start(10);
        return true;
    }
    void Tick()
    {
        if (!surface || !output || !cover) return;
        const HWND source = reinterpret_cast<HWND>(surface->winId());
        RECT r{}; GetClientRect(source, &r);
        POINT p{}; ClientToScreen(source, &p);
        OffsetRect(&r, p.x, p.y);
        bool changed = !EqualRect(&previous, &r);
        if (changed)
        {
            if (ready) ResetEvent(ready);
            presented = false;
            began = GetTickCount64();
            previous = r;
            const int w = r.right-r.left, h = r.bottom-r.top;
            SetWindowPos(output, nullptr, r.left,r.top,w,h, SWP_NOACTIVATE | SWP_NOZORDER);
            SetWindowPos(cover, nullptr, r.left,r.top,w,h, SWP_NOACTIVATE | SWP_NOZORDER);
        }
        const bool visible = IsWindowVisible(source) && !IsIconic(capture);
        ShowWindow(output, visible ? SW_SHOWNOACTIVATE : SW_HIDE);
        if (process && !failed && WaitForSingleObject(process,0) == WAIT_OBJECT_0)
        {
            DWORD code = 0; GetExitCodeProcess(process,&code);
            Fail(QString("Worker exited, code %1").arg(code));
        }
        if (!failed && ready && WaitForSingleObject(ready,0) == WAIT_OBJECT_0)
        {
            if (!presented) Log("filtered presentation ready; opening gate");
            presented = true;
        }
        if (!failed && !presented && GetTickCount64()-began > 30000)
            Fail("No filtered frame within 30 seconds");
        ShowWindow(cover, visible && (!presented || failed) ? SW_SHOWNOACTIVATE : SW_HIDE);
    }
    bool eventFilter(QObject*, QEvent* event) override
    {
        if (event->type() == QEvent::Resize || event->type() == QEvent::Move ||
            event->type() == QEvent::Show || event->type() == QEvent::Hide || event->type() == QEvent::Expose)
            Tick();
        return false;
    }
};
inline Bridge* Instance() { static Bridge* b = new Bridge(); return b; }
inline bool Attach(QWindow* w, std::function<void()> pause) { return !Enabled() || Instance()->Start(w, std::move(pause)); }
inline bool HasGate() { return !Enabled() || (Instance()->output && Instance()->cover); }
inline void Detach() { if (Enabled()) { Log("display released"); Instance()->Close(); } }
inline void Cursor(bool hidden)
{
    if (!Enabled()) return;
    auto b = Instance();
    if (b->hiddenCursor != hidden) Log(hidden ? "cursor hidden" : "cursor visible");
    b->hiddenCursor = hidden;
}
}
#else
namespace ShaderPrototype { inline bool Enabled() { return false; } }
#endif
