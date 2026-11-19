from __future__ import annotations

import ctypes
import os
import queue
import sys
import threading
import time
from typing import Callable

if os.name == "nt":
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    shell32 = ctypes.windll.shell32
    kernel32 = ctypes.windll.kernel32
    gdi32 = ctypes.windll.gdi32
    ole32 = ctypes.windll.ole32

    WPARAM = ctypes.c_size_t
    LPARAM = ctypes.c_ssize_t
    LRESULT = ctypes.c_ssize_t
    WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, WPARAM, LPARAM)
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, LPARAM)

    # Window & Tray constants
    WM_NULL = 0x0000
    WM_DESTROY = 0x0002
    WM_CLOSE = 0x0010
    WM_USER = 0x0400
    WM_TRAYICON = WM_USER + 1
    WM_PICK_FOLDER = WM_USER + 2
    WS_POPUP = 0x80000000
    WS_VISIBLE = 0x10000000
    WS_EX_TOOLWINDOW = 0x00000080
    WS_EX_LAYERED = 0x00080000
    LWA_ALPHA = 0x00000002
    ASFW_ANY = 0xFFFFFFFF
    SW_SHOWNORMAL = 1
    SW_RESTORE = 9
    SM_CXSCREEN = 0
    SM_CYSCREEN = 1
    WM_LBUTTONUP = 0x0202
    WM_LBUTTONDBLCLK = 0x0203
    WM_RBUTTONUP = 0x0205
    WM_CONTEXTMENU = 0x007B
    WM_SETTINGCHANGE = 0x001A
    WM_THEMECHANGED = 0x031A

    NIM_ADD = 0x00000000
    NIM_DELETE = 0x00000002
    NIF_MESSAGE = 0x00000001
    NIF_ICON = 0x00000002
    NIF_TIP = 0x00000004

    MF_STRING = 0x00000000
    MF_GRAYED = 0x00000001
    MF_POPUP = 0x00000010
    MF_SEPARATOR = 0x00000800
    TPM_LEFTALIGN = 0x0000
    TPM_TOPALIGN = 0x0000
    TPM_RIGHTBUTTON = 0x0002
    TPM_RIGHTALIGN = 0x0008
    TPM_BOTTOMALIGN = 0x0020
    TPM_NONOTIFY = 0x0080
    TPM_RETURNCMD = 0x0100

    MONITOR_DEFAULTTONEAREST = 0x00000002
    SPI_GETHIGHCONTRAST = 0x0042
    HCF_HIGHCONTRASTON = 0x00000001

    PREFERRED_APP_MODE_DEFAULT = 0
    PREFERRED_APP_MODE_ALLOW_DARK = 1
    PREFERRED_APP_MODE_FORCE_DARK = 2
    PREFERRED_APP_MODE_FORCE_LIGHT = 3

    IDI_APPLICATION = 32512
    DIB_RGB_COLORS = 0
    BI_BITFIELDS = 3

    # Menu command IDs
    CMD_OPEN = 1001
    CMD_STOP_ALL = 1002
    CMD_EXIT = 1003
    CMD_PROJECT_BASE = 2000

    # COM / IFileOpenDialog constants
    COINIT_APARTMENTTHREADED = 0x2
    COINIT_DISABLE_OLE1DDE = 0x4
    CLSCTX_INPROC_SERVER = 0x1
    FOS_PICKFOLDERS = 0x00000020
    FOS_FORCEFILESYSTEM = 0x00000040
    FOS_PATHMUSTEXIST = 0x00000800
    SIGDN_FILESYSPATH = 0x80058000
    HRESULT_CANCELLED = -2147023673  # 0x800704C7

    class GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", wintypes.DWORD),
            ("Data2", wintypes.WORD),
            ("Data3", wintypes.WORD),
            ("Data4", ctypes.c_ubyte * 8),
        ]

        @classmethod
        def from_str(cls, text: str) -> GUID:
            cleaned = text.strip("{}").replace("-", "")
            d1 = int(cleaned[0:8], 16)
            d2 = int(cleaned[8:12], 16)
            d3 = int(cleaned[12:16], 16)
            d4 = (ctypes.c_ubyte * 8)(*(int(cleaned[16 + i * 2 : 18 + i * 2], 16) for i in range(8)))
            return cls(d1, d2, d3, d4)

    CLSID_FileOpenDialog = GUID.from_str("{DC1C5A9C-E88A-4DDE-A5A1-60F82A20AEF7}")
    IID_IFileOpenDialog = GUID.from_str("{D57C7288-D4AD-4768-BE02-9D969532D960}")

    class WNDCLASSEXW(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.UINT),
            ("style", wintypes.UINT),
            ("lpfnWndProc", WNDPROC),
            ("cbClsExtra", ctypes.c_int),
            ("cbWndExtra", ctypes.c_int),
            ("hInstance", wintypes.HINSTANCE),
            ("hIcon", wintypes.HICON),
            ("hCursor", wintypes.HANDLE),
            ("hbrBackground", wintypes.HANDLE),
            ("lpszMenuName", wintypes.LPCWSTR),
            ("lpszClassName", wintypes.LPCWSTR),
            ("hIconSm", wintypes.HICON),
        ]

    class NOTIFYICONDATAW(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("hWnd", wintypes.HWND),
            ("uID", wintypes.UINT),
            ("uFlags", wintypes.UINT),
            ("uCallbackMessage", wintypes.UINT),
            ("hIcon", wintypes.HICON),
            ("szTip", wintypes.WCHAR * 128),
        ]

    class BITMAPV5HEADER(ctypes.Structure):
        _fields_ = [
            ("bV5Size", wintypes.DWORD),
            ("bV5Width", wintypes.LONG),
            ("bV5Height", wintypes.LONG),
            ("bV5Planes", wintypes.WORD),
            ("bV5BitCount", wintypes.WORD),
            ("bV5Compression", wintypes.DWORD),
            ("bV5SizeImage", wintypes.DWORD),
            ("bV5XPelsPerMeter", wintypes.LONG),
            ("bV5YPelsPerMeter", wintypes.LONG),
            ("bV5ClrUsed", wintypes.DWORD),
            ("bV5ClrImportant", wintypes.DWORD),
            ("bV5RedMask", wintypes.DWORD),
            ("bV5GreenMask", wintypes.DWORD),
            ("bV5BlueMask", wintypes.DWORD),
            ("bV5AlphaMask", wintypes.DWORD),
            ("bV5CSType", wintypes.DWORD),
            ("bV5Endpoints", ctypes.c_byte * 36),
            ("bV5GammaRed", wintypes.DWORD),
            ("bV5GammaGreen", wintypes.DWORD),
            ("bV5GammaBlue", wintypes.DWORD),
            ("bV5Intent", wintypes.DWORD),
            ("bV5ProfileData", wintypes.DWORD),
            ("bV5ProfileSize", wintypes.DWORD),
            ("bV5Reserved", wintypes.DWORD),
        ]

    class ICONINFO(ctypes.Structure):
        _fields_ = [
            ("fIcon", wintypes.BOOL),
            ("xHotspot", wintypes.DWORD),
            ("yHotspot", wintypes.DWORD),
            ("hbmMask", wintypes.HBITMAP),
            ("hbmColor", wintypes.HBITMAP),
        ]

    class BROWSEINFOW(ctypes.Structure):
        _fields_ = [
            ("hwndOwner", wintypes.HWND),
            ("pidlRoot", ctypes.c_void_p),
            ("pszDisplayName", wintypes.LPWSTR),
            ("lpszTitle", wintypes.LPCWSTR),
            ("ulFlags", wintypes.UINT),
            ("lpfn", ctypes.c_void_p),
            ("lParam", LPARAM),
            ("iImage", ctypes.c_int),
        ]

    class MONITORINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("rcMonitor", wintypes.RECT),
            ("rcWork", wintypes.RECT),
            ("dwFlags", wintypes.DWORD),
        ]

    class HIGHCONTRASTW(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.UINT),
            ("dwFlags", wintypes.DWORD),
            ("lpszDefaultScheme", wintypes.LPWSTR),
        ]

    # Configure critical Win32 signatures for 64-bit safety
    user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, WPARAM, LPARAM]
    user32.DefWindowProcW.restype = LRESULT
    user32.RegisterClassExW.argtypes = [ctypes.POINTER(WNDCLASSEXW)]
    user32.RegisterClassExW.restype = wintypes.ATOM
    user32.CreateWindowExW.argtypes = [
        wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
        ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
        wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID,
    ]
    user32.CreateWindowExW.restype = wintypes.HWND
    user32.DestroyWindow.argtypes = [wintypes.HWND]
    user32.DestroyWindow.restype = wintypes.BOOL
    user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, WPARAM, LPARAM]
    user32.PostMessageW.restype = wintypes.BOOL
    user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
    user32.GetMessageW.restype = wintypes.BOOL
    user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
    user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
    user32.RegisterWindowMessageW.argtypes = [wintypes.LPCWSTR]
    user32.RegisterWindowMessageW.restype = wintypes.UINT
    user32.CreatePopupMenu.restype = wintypes.HMENU
    user32.AppendMenuW.argtypes = [wintypes.HMENU, wintypes.UINT, WPARAM, wintypes.LPCWSTR]
    user32.AppendMenuW.restype = wintypes.BOOL
    user32.TrackPopupMenu.argtypes = [
        wintypes.HMENU, wintypes.UINT, ctypes.c_int, ctypes.c_int,
        ctypes.c_int, wintypes.HWND, ctypes.c_void_p,
    ]
    user32.TrackPopupMenu.restype = wintypes.BOOL
    user32.DestroyMenu.argtypes = [wintypes.HMENU]
    user32.SetMenuDefaultItem.argtypes = [wintypes.HMENU, wintypes.UINT, wintypes.UINT]
    user32.SetMenuDefaultItem.restype = wintypes.BOOL
    user32.MonitorFromPoint.argtypes = [wintypes.POINT, wintypes.DWORD]
    user32.MonitorFromPoint.restype = wintypes.HMONITOR
    user32.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.POINTER(MONITORINFO)]
    user32.GetMonitorInfoW.restype = wintypes.BOOL
    user32.SystemParametersInfoW.argtypes = [wintypes.UINT, wintypes.UINT, ctypes.c_void_p, wintypes.UINT]
    user32.SystemParametersInfoW.restype = wintypes.BOOL
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
    user32.LoadIconW.argtypes = [wintypes.HINSTANCE, ctypes.c_void_p]
    user32.LoadIconW.restype = wintypes.HICON
    user32.CreateIconIndirect.argtypes = [ctypes.POINTER(ICONINFO)]
    user32.CreateIconIndirect.restype = wintypes.HICON
    user32.DestroyIcon.argtypes = [wintypes.HICON]
    user32.GetDC.argtypes = [wintypes.HWND]
    user32.GetDC.restype = wintypes.HDC
    user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]

    shell32.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.POINTER(NOTIFYICONDATAW)]
    shell32.Shell_NotifyIconW.restype = wintypes.BOOL
    shell32.SHBrowseForFolderW.argtypes = [ctypes.POINTER(BROWSEINFOW)]
    shell32.SHBrowseForFolderW.restype = ctypes.c_void_p
    shell32.SHGetPathFromIDListW.argtypes = [ctypes.c_void_p, wintypes.LPWSTR]
    shell32.SHGetPathFromIDListW.restype = wintypes.BOOL

    kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
    kernel32.GetModuleHandleW.restype = wintypes.HMODULE

    ole32.CoInitializeEx.argtypes = [ctypes.c_void_p, wintypes.DWORD]
    ole32.CoInitializeEx.restype = ctypes.c_long
    ole32.CoUninitialize.argtypes = []
    ole32.CoCreateInstance.argtypes = [
        ctypes.POINTER(GUID), ctypes.c_void_p, wintypes.DWORD,
        ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p),
    ]
    ole32.CoCreateInstance.restype = ctypes.c_long
    ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]

    gdi32.CreateDIBSection.argtypes = [
        wintypes.HDC, ctypes.POINTER(BITMAPV5HEADER), wintypes.UINT,
        ctypes.POINTER(ctypes.c_void_p), wintypes.HANDLE, wintypes.DWORD,
    ]
    gdi32.CreateDIBSection.restype = wintypes.HBITMAP
    gdi32.CreateBitmap.argtypes = [ctypes.c_int, ctypes.c_int, wintypes.UINT, wintypes.UINT, ctypes.c_void_p]
    gdi32.CreateBitmap.restype = wintypes.HBITMAP
    gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]

    user32.GetForegroundWindow.argtypes = []
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
    user32.AttachThreadInput.restype = wintypes.BOOL
    user32.BringWindowToTop.argtypes = [wintypes.HWND]
    user32.BringWindowToTop.restype = wintypes.BOOL
    user32.AllowSetForegroundWindow.argtypes = [wintypes.DWORD]
    user32.AllowSetForegroundWindow.restype = wintypes.BOOL
    user32.EnumWindows.argtypes = [WNDENUMPROC, LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL
    user32.IsIconic.argtypes = [wintypes.HWND]
    user32.IsIconic.restype = wintypes.BOOL
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.ShowWindow.restype = wintypes.BOOL
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetClassNameW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    shell32.ShellExecuteW.argtypes = [
        wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR,
        wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.c_int,
    ]
    shell32.ShellExecuteW.restype = ctypes.c_void_p
    user32.SetLayeredWindowAttributes.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_ubyte, wintypes.DWORD]
    user32.SetLayeredWindowAttributes.restype = wintypes.BOOL
    user32.GetSystemMetrics.argtypes = [ctypes.c_int]
    user32.GetSystemMetrics.restype = ctypes.c_int
    kernel32.GetCurrentThreadId.argtypes = []
    kernel32.GetCurrentThreadId.restype = wintypes.DWORD

    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
    JobObjectExtendedLimitInformation = 9
    PROCESS_SET_QUOTA = 0x0100
    PROCESS_TERMINATE = 0x0001

    class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_int64),
            ("PerJobUserTimeLimit", ctypes.c_int64),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class IO_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("ReadOperationCount", ctypes.c_uint64),
            ("WriteOperationCount", ctypes.c_uint64),
            ("OtherOperationCount", ctypes.c_uint64),
            ("ReadTransferCount", ctypes.c_uint64),
            ("WriteTransferCount", ctypes.c_uint64),
            ("OtherTransferCount", ctypes.c_uint64),
        ]

    class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
            ("IoInfo", IO_COUNTERS),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    kernel32.SetInformationJobObject.restype = wintypes.BOOL
    kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel32.TerminateJobObject.restype = wintypes.BOOL
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    _kernel32_last_error = ctypes.WinDLL("kernel32", use_last_error=True)
    _kernel32_last_error.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    _kernel32_last_error.CreateMutexW.restype = wintypes.HANDLE
    ERROR_ALREADY_EXISTS = 183


_DPI_AWARENESS_SET = False


def enable_dpi_awareness() -> None:
    global _DPI_AWARENESS_SET
    if os.name != "nt" or _DPI_AWARENESS_SET:
        return
    _DPI_AWARENESS_SET = True
    try:
        # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
        user32.SetProcessDpiAwarenessContext(ctypes.c_ssize_t(-4))
    except Exception:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                user32.SetProcessDPIAware()
            except Exception:
                pass


def _com_method(obj: ctypes.c_void_p, index: int, restype, *argtypes):
    vtable = ctypes.cast(obj, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    fn_type = ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)
    return fn_type(vtable[index])


def _create_foreground_owner() -> wintypes.HWND | None:
    hinst = kernel32.GetModuleHandleW(None)
    cx = max(100, user32.GetSystemMetrics(SM_CXSCREEN) // 2)
    cy = max(100, user32.GetSystemMetrics(SM_CYSCREEN) // 2)
    owner = user32.CreateWindowExW(
        WS_EX_TOOLWINDOW | WS_EX_LAYERED,
        "STATIC",
        "",
        WS_POPUP | WS_VISIBLE,
        cx, cy, 1, 1,
        None, None, hinst, None,
    )
    if not owner:
        return None
    user32.SetLayeredWindowAttributes(owner, 0, 0, LWA_ALPHA)
    fg = user32.GetForegroundWindow()
    cur_tid = kernel32.GetCurrentThreadId()
    fg_tid = user32.GetWindowThreadProcessId(fg, None) if fg else 0
    attached = bool(fg_tid and fg_tid != cur_tid and user32.AttachThreadInput(cur_tid, fg_tid, True))
    try:
        user32.SetForegroundWindow(owner)
        user32.BringWindowToTop(owner)
    finally:
        if attached:
            user32.AttachThreadInput(cur_tid, fg_tid, False)
    return owner


def _select_folder_ifileopendialog(title: str) -> str | None:
    hr = ole32.CoInitializeEx(None, COINIT_APARTMENTTHREADED | COINIT_DISABLE_OLE1DDE)
    initialized = hr in (0, 1)  # S_OK or S_FALSE
    dialog = ctypes.c_void_p()
    item = ctypes.c_void_p()
    path_ptr = wintypes.LPWSTR()
    owner = _create_foreground_owner()
    try:
        res = ole32.CoCreateInstance(
            ctypes.byref(CLSID_FileOpenDialog),
            None,
            CLSCTX_INPROC_SERVER,
            ctypes.byref(IID_IFileOpenDialog),
            ctypes.byref(dialog),
        )
        if res != 0 or not dialog:
            raise OSError(f"CoCreateInstance failed: 0x{res & 0xFFFFFFFF:08X}")

        get_options = _com_method(dialog, 10, ctypes.c_long, ctypes.POINTER(wintypes.DWORD))
        set_options = _com_method(dialog, 9, ctypes.c_long, wintypes.DWORD)
        set_title = _com_method(dialog, 17, ctypes.c_long, wintypes.LPCWSTR)
        show = _com_method(dialog, 3, ctypes.c_long, wintypes.HWND)
        get_result = _com_method(dialog, 20, ctypes.c_long, ctypes.POINTER(ctypes.c_void_p))

        options = wintypes.DWORD()
        get_options(dialog, ctypes.byref(options))
        set_options(dialog, options.value | FOS_PICKFOLDERS | FOS_FORCEFILESYSTEM | FOS_PATHMUSTEXIST)
        set_title(dialog, title)

        show_hr = show(dialog, owner)
        if show_hr == HRESULT_CANCELLED:
            return None
        if show_hr != 0:
            raise OSError(f"IFileOpenDialog::Show failed: 0x{show_hr & 0xFFFFFFFF:08X}")

        if get_result(dialog, ctypes.byref(item)) != 0 or not item:
            return None

        get_display_name = _com_method(item, 5, ctypes.c_long, wintypes.DWORD, ctypes.POINTER(wintypes.LPWSTR))
        if get_display_name(item, SIGDN_FILESYSPATH, ctypes.byref(path_ptr)) == 0 and path_ptr:
            return path_ptr.value
        return None
    finally:
        if owner:
            user32.DestroyWindow(owner)
        if path_ptr:
            ole32.CoTaskMemFree(path_ptr)
        if item:
            _com_method(item, 2, ctypes.c_ulong)(item)
        if dialog:
            _com_method(dialog, 2, ctypes.c_ulong)(dialog)
        if initialized:
            ole32.CoUninitialize()


def _select_folder_shbrowse(title: str) -> str | None:
    owner = _create_foreground_owner()
    display_name = ctypes.create_unicode_buffer(260)
    bi = BROWSEINFOW()
    bi.hwndOwner = owner
    bi.lpszTitle = title
    bi.pszDisplayName = ctypes.cast(display_name, wintypes.LPWSTR)
    bi.ulFlags = 0x00000041  # BIF_RETURNONLYFSDIRS | BIF_NEWDIALOGSTYLE
    try:
        pidl = shell32.SHBrowseForFolderW(ctypes.byref(bi))
        if not pidl:
            return None
        try:
            out = ctypes.create_unicode_buffer(32768)
            if shell32.SHGetPathFromIDListW(pidl, out):
                return out.value or None
            return None
        finally:
            ole32.CoTaskMemFree(pidl)
    finally:
        if owner:
            user32.DestroyWindow(owner)


_TRAY_HWND_LOCK = threading.Lock()
_ACTIVE_TRAY_HWND: wintypes.HWND | None = None
_TRAY_PICK_REQUESTS: queue.Queue[tuple[str, threading.Event, dict[str, object]]] = queue.Queue()


def _select_folder_on_current_thread(title: str) -> str | None:
    try:
        return _select_folder_ifileopendialog(title)
    except Exception:
        return _select_folder_shbrowse(title)


def select_folder_native(title: str = "选择项目文件夹") -> str | None:
    if os.name != "nt":
        raise RuntimeError("当前系统不支持 Win32 原生文件夹选择器")
    enable_dpi_awareness()
    with _TRAY_HWND_LOCK:
        tray_hwnd = _ACTIVE_TRAY_HWND
    if tray_hwnd:
        done = threading.Event()
        box: dict[str, object] = {}
        _TRAY_PICK_REQUESTS.put((title, done, box))
        if user32.PostMessageW(tray_hwnd, WM_PICK_FOLDER, 0, 0):
            done.wait()
            if "error" in box:
                raise box["error"]  # type: ignore[misc]
            return box.get("path")  # type: ignore[return-value]
    return _select_folder_on_current_thread(title)


_PERSONALIZE_REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
_UXTHEME_LOADED = False
_UXTHEME_ALLOW_DARK_WINDOW = None
_UXTHEME_SET_PREFERRED_APP_MODE = None
_UXTHEME_ALLOW_DARK_APP = None
_UXTHEME_FLUSH_MENU_THEMES = None
_APPLIED_APP_MODE: int | None = None


def _ensure_uxtheme_loaded() -> None:
    global _UXTHEME_LOADED
    global _UXTHEME_ALLOW_DARK_WINDOW
    global _UXTHEME_SET_PREFERRED_APP_MODE
    global _UXTHEME_ALLOW_DARK_APP
    global _UXTHEME_FLUSH_MENU_THEMES
    if os.name != "nt" or _UXTHEME_LOADED:
        return
    _UXTHEME_LOADED = True
    try:
        build = sys.getwindowsversion().build
        if build < 17763:
            return
        uxtheme = ctypes.WinDLL("uxtheme")
    except Exception:
        return

    try:
        fn_window = uxtheme[133]
        fn_window.argtypes = [wintypes.HWND, wintypes.BOOL]
        fn_window.restype = wintypes.BOOL
        _UXTHEME_ALLOW_DARK_WINDOW = fn_window
    except Exception:
        pass

    try:
        fn_app = uxtheme[135]
        if build >= 18362:
            fn_app.argtypes = [ctypes.c_int]
            fn_app.restype = ctypes.c_int
            _UXTHEME_SET_PREFERRED_APP_MODE = fn_app
        else:
            fn_app.argtypes = [wintypes.BOOL]
            fn_app.restype = wintypes.BOOL
            _UXTHEME_ALLOW_DARK_APP = fn_app
    except Exception:
        pass

    try:
        fn_flush = uxtheme[136]
        fn_flush.argtypes = []
        fn_flush.restype = None
        _UXTHEME_FLUSH_MENU_THEMES = fn_flush
    except Exception:
        pass


def _read_light_theme_flag(value_name: str) -> bool | None:
    if os.name != "nt":
        return None
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _PERSONALIZE_REG_PATH) as key:
            value, _reg_type = winreg.QueryValueEx(key, value_name)
            return bool(value)
    except OSError:
        return None


def is_system_dark_mode() -> bool:
    """Return True when the Windows taskbar/system theme is dark."""
    flag = _read_light_theme_flag("SystemUsesLightTheme")
    if flag is None:
        flag = _read_light_theme_flag("AppsUseLightTheme")
    return flag is False


def is_apps_dark_mode() -> bool:
    """Return True when the Windows default app theme is dark."""
    flag = _read_light_theme_flag("AppsUseLightTheme")
    if flag is None:
        flag = _read_light_theme_flag("SystemUsesLightTheme")
    return flag is False


def _is_high_contrast_enabled() -> bool:
    if os.name != "nt":
        return False
    try:
        hc = HIGHCONTRASTW()
        hc.cbSize = ctypes.sizeof(HIGHCONTRASTW)
        if user32.SystemParametersInfoW(SPI_GETHIGHCONTRAST, hc.cbSize, ctypes.byref(hc), 0):
            return bool(hc.dwFlags & HCF_HIGHCONTRASTON)
    except Exception:
        pass
    return False


def _apply_menu_theme(hwnd: int | None, *, prefer_system_theme: bool = True, force: bool = False) -> bool:
    """Synchronize Win32 popup menu dark/light mode with Windows theme settings."""
    global _APPLIED_APP_MODE
    if os.name != "nt":
        return False
    _ensure_uxtheme_loaded()
    if _is_high_contrast_enabled():
        desired_mode = PREFERRED_APP_MODE_DEFAULT
        window_dark = False
    elif prefer_system_theme:
        window_dark = is_system_dark_mode()
        desired_mode = PREFERRED_APP_MODE_FORCE_DARK if window_dark else PREFERRED_APP_MODE_FORCE_LIGHT
    else:
        window_dark = is_apps_dark_mode()
        desired_mode = PREFERRED_APP_MODE_ALLOW_DARK

    if not force and desired_mode == _APPLIED_APP_MODE:
        return window_dark

    try:
        if _UXTHEME_SET_PREFERRED_APP_MODE is not None:
            _UXTHEME_SET_PREFERRED_APP_MODE(desired_mode)
        elif _UXTHEME_ALLOW_DARK_APP is not None:
            _UXTHEME_ALLOW_DARK_APP(bool(window_dark))
        if hwnd and _UXTHEME_ALLOW_DARK_WINDOW is not None:
            _UXTHEME_ALLOW_DARK_WINDOW(hwnd, bool(window_dark))
        if _UXTHEME_FLUSH_MENU_THEMES is not None:
            _UXTHEME_FLUSH_MENU_THEMES()
        _APPLIED_APP_MODE = desired_mode
    except Exception:
        pass
    return window_dark


def _escape_menu_text(text: str, max_len: int = 40) -> str:
    cleaned = text.strip()
    if len(cleaned) > max_len:
        cleaned = cleaned[: max_len - 1].rstrip() + "…"
    return cleaned.replace("&", "&&")


def _popup_alignment_flags(pt) -> int:
    h_align = TPM_RIGHTALIGN
    v_align = TPM_BOTTOMALIGN
    try:
        hmon = user32.MonitorFromPoint(pt, MONITOR_DEFAULTTONEAREST)
        if hmon:
            mi = MONITORINFO()
            mi.cbSize = ctypes.sizeof(MONITORINFO)
            if user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
                mid_x = (mi.rcWork.left + mi.rcWork.right) // 2
                mid_y = (mi.rcWork.top + mi.rcWork.bottom) // 2
                h_align = TPM_RIGHTALIGN if pt.x >= mid_x else TPM_LEFTALIGN
                v_align = TPM_BOTTOMALIGN if pt.y >= mid_y else TPM_TOPALIGN
    except Exception:
        pass
    return h_align | v_align | TPM_RIGHTBUTTON | TPM_RETURNCMD | TPM_NONOTIFY


def _create_brand_icon() -> wintypes.HICON:
    """Create a 32x32 RGBA tray icon in memory with zero external image dependencies."""
    size = 32
    header = BITMAPV5HEADER()
    header.bV5Size = ctypes.sizeof(BITMAPV5HEADER)
    header.bV5Width = size
    header.bV5Height = -size  # top-down DIB
    header.bV5Planes = 1
    header.bV5BitCount = 32
    header.bV5Compression = BI_BITFIELDS
    header.bV5RedMask = 0x00FF0000
    header.bV5GreenMask = 0x0000FF00
    header.bV5BlueMask = 0x000000FF
    header.bV5AlphaMask = 0xFF000000

    bits = ctypes.c_void_p()
    hdc = user32.GetDC(None)
    hbm_color = gdi32.CreateDIBSection(hdc, ctypes.byref(header), DIB_RGB_COLORS, ctypes.byref(bits), None, 0)
    user32.ReleaseDC(None, hdc)
    if not hbm_color or not bits:
        return user32.LoadIconW(None, ctypes.c_void_p(IDI_APPLICATION))

    pixels = (ctypes.c_uint32 * (size * size)).from_address(bits.value)
    bg = 0xFF176B57  # brand teal (matches --accent)
    fg = 0xFFFFFFFF  # white play triangle
    for y in range(size):
        for x in range(size):
            # Rounded square mask (radius ~6)
            dx = max(4 - x, 0, x - (size - 5))
            dy = max(4 - y, 0, y - (size - 5))
            if dx * dx + dy * dy <= 16:
                pixels[y * size + x] = bg
            else:
                pixels[y * size + x] = 0x00000000

    # Draw crisp white play triangle in center
    for y in range(9, 23):
        half_span = 7 - abs(y - 16)
        for x in range(11, 11 + max(1, half_span * 2 - 1)):
            if 0 <= x < size:
                pixels[y * size + x] = fg

    hbm_mask = gdi32.CreateBitmap(size, size, 1, 1, None)
    icon_info = ICONINFO(True, 0, 0, hbm_mask, hbm_color)
    hicon = user32.CreateIconIndirect(ctypes.byref(icon_info))
    gdi32.DeleteObject(hbm_color)
    if hbm_mask:
        gdi32.DeleteObject(hbm_mask)
    return hicon or user32.LoadIconW(None, ctypes.c_void_p(IDI_APPLICATION))


class TrayManager:
    """Lightweight Windows system tray icon and menu backed purely by Win32 ctypes."""

    def __init__(
        self,
        tooltip: str,
        on_open: Callable[[], None],
        on_stop_all: Callable[[], None],
        on_exit: Callable[[], None],
        get_running_count: Callable[[], int],
        get_running_projects: Callable[[], list[dict[str, object]]] | None = None,
        on_open_project: Callable[[str], None] | None = None,
    ) -> None:
        self.tooltip = tooltip[:127]
        self.on_open = on_open
        self.on_stop_all = on_stop_all
        self.on_exit = on_exit
        self.get_running_count = get_running_count
        self.get_running_projects = get_running_projects
        self.on_open_project = on_open_project
        self.hwnd: wintypes.HWND | None = None
        self._hicon: wintypes.HICON | None = None
        self._wndproc_ref = None
        self._exit_requested = False
        self._menu_open = False
        self._taskbar_created_msg = user32.RegisterWindowMessageW("TaskbarCreated") if os.name == "nt" else 0

    def _add_notify_icon(self) -> None:
        nid = NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        nid.hWnd = self.hwnd
        nid.uID = 1
        nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        nid.uCallbackMessage = WM_TRAYICON
        nid.hIcon = self._hicon
        nid.szTip = self.tooltip
        shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid))

    def _remove_notify_icon(self) -> None:
        if not self.hwnd:
            return
        nid = NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        nid.hWnd = self.hwnd
        nid.uID = 1
        shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(nid))

    def _sync_theme(self, *, force: bool = False) -> None:
        _apply_menu_theme(self.hwnd, prefer_system_theme=True, force=force)

    def _show_context_menu(self) -> None:
        if self._menu_open:
            return
        self._menu_open = True
        self._sync_theme()
        menu = user32.CreatePopupMenu()
        if not menu:
            self._menu_open = False
            return
        project_urls: dict[int, str] = {}
        try:
            running_projects = self.get_running_projects() if self.get_running_projects else []
            running = len(running_projects) if self.get_running_projects else self.get_running_count()

            user32.AppendMenuW(menu, MF_STRING, CMD_OPEN, "打开控制台")
            user32.SetMenuDefaultItem(menu, CMD_OPEN, 0)
            user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)

            if running_projects and self.on_open_project:
                submenu = user32.CreatePopupMenu()
                if submenu:
                    for index, project in enumerate(running_projects):
                        cmd_id = CMD_PROJECT_BASE + index
                        name = _escape_menu_text(str(project.get("name", "未命名项目")))
                        port = project.get("port")
                        label = f"{name}  (:{port})" if port is not None else name
                        user32.AppendMenuW(submenu, MF_STRING, cmd_id, label)
                        url = project.get("url")
                        if url:
                            project_urls[cmd_id] = str(url)
                    if not user32.AppendMenuW(menu, MF_POPUP, int(submenu), f"运行中项目（{running}）"):
                        user32.DestroyMenu(submenu)
                        user32.AppendMenuW(menu, MF_STRING | MF_GRAYED, 0, f"运行中项目：{running} 个")
                else:
                    user32.AppendMenuW(menu, MF_STRING | MF_GRAYED, 0, f"运行中项目：{running} 个")
            else:
                user32.AppendMenuW(menu, MF_STRING | MF_GRAYED, 0, f"运行中项目：{running} 个")

            stop_flags = MF_STRING if running > 0 else (MF_STRING | MF_GRAYED)
            user32.AppendMenuW(menu, stop_flags, CMD_STOP_ALL, "停止全部项目")
            user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
            user32.AppendMenuW(menu, MF_STRING, CMD_EXIT, "退出启动器")

            pt = wintypes.POINT()
            user32.GetCursorPos(ctypes.byref(pt))
            user32.SetForegroundWindow(self.hwnd)
            cmd = user32.TrackPopupMenu(
                menu,
                _popup_alignment_flags(pt),
                pt.x,
                pt.y,
                0,
                self.hwnd,
                None,
            )
            user32.PostMessageW(self.hwnd, WM_NULL, 0, 0)
            if cmd == CMD_OPEN:
                self.on_open()
            elif cmd in project_urls and self.on_open_project:
                self.on_open_project(project_urls[cmd])
            elif cmd == CMD_STOP_ALL:
                threading.Thread(target=self.on_stop_all, daemon=True).start()
            elif cmd == CMD_EXIT:
                self._exit_requested = True
                self.stop()
        finally:
            user32.DestroyMenu(menu)
            self._menu_open = False
            if is_system_dark_mode() != is_apps_dark_mode():
                _apply_menu_theme(self.hwnd, prefer_system_theme=False)

    def _wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == WM_PICK_FOLDER:
            if is_system_dark_mode() != is_apps_dark_mode():
                _apply_menu_theme(hwnd, prefer_system_theme=False)
            while True:
                try:
                    title, done, box = _TRAY_PICK_REQUESTS.get_nowait()
                except queue.Empty:
                    break
                try:
                    box["path"] = _select_folder_on_current_thread(title)
                except Exception as exc:
                    box["error"] = exc
                finally:
                    done.set()
            return 0
        if msg == WM_SETTINGCHANGE:
            setting = ""
            if lparam:
                try:
                    setting = ctypes.wstring_at(lparam)
                except Exception:
                    setting = ""
            if not setting or setting == "ImmersiveColorSet":
                self._sync_theme(force=True)
            return 0
        if msg == WM_THEMECHANGED:
            self._sync_theme(force=True)
            return 0
        if msg == self._taskbar_created_msg and self._taskbar_created_msg:
            self._add_notify_icon()
            return 0
        if msg == WM_TRAYICON:
            if lparam in (WM_LBUTTONUP, WM_LBUTTONDBLCLK):
                self.on_open()
            elif lparam in (WM_RBUTTONUP, WM_CONTEXTMENU):
                self._show_context_menu()
            return 0
        if msg == WM_CLOSE:
            user32.DestroyWindow(hwnd)
            return 0
        if msg == WM_DESTROY:
            self._remove_notify_icon()
            user32.PostQuitMessage(0)
            return 0
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def run(self) -> None:
        if os.name != "nt":
            return
        global _ACTIVE_TRAY_HWND
        hr = ole32.CoInitializeEx(None, COINIT_APARTMENTTHREADED | COINIT_DISABLE_OLE1DDE)
        com_initialized = hr in (0, 1)
        enable_dpi_awareness()
        hinst = kernel32.GetModuleHandleW(None)
        class_name = "WebRouterTrayWindow"
        self._wndproc_ref = WNDPROC(self._wnd_proc)
        wc = WNDCLASSEXW()
        wc.cbSize = ctypes.sizeof(WNDCLASSEXW)
        wc.lpfnWndProc = self._wndproc_ref
        wc.hInstance = hinst
        wc.lpszClassName = class_name
        user32.RegisterClassExW(ctypes.byref(wc))

        self._hicon = _create_brand_icon()
        self.hwnd = user32.CreateWindowExW(
            0, class_name, self.tooltip, 0,
            0, 0, 0, 0,
            None, None, hinst, None,
        )
        with _TRAY_HWND_LOCK:
            _ACTIVE_TRAY_HWND = self.hwnd
        self._sync_theme(force=True)
        self._add_notify_icon()

        try:
            msg = wintypes.MSG()
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            with _TRAY_HWND_LOCK:
                if _ACTIVE_TRAY_HWND == self.hwnd:
                    _ACTIVE_TRAY_HWND = None
            if self._hicon:
                user32.DestroyIcon(self._hicon)
                self._hicon = None
            self.hwnd = None
            if com_initialized:
                ole32.CoUninitialize()
        if self._exit_requested:
            self.on_exit()

    def stop(self) -> None:
        if self.hwnd:
            user32.PostMessageW(self.hwnd, WM_CLOSE, 0, 0)


class ProcessJob:
    """Windows Job Object with KILL_ON_JOB_CLOSE so child trees never outlive the launcher."""

    def __init__(self) -> None:
        self._handle: int | None = None
        if os.name != "nt":
            return
        handle = kernel32.CreateJobObjectW(None, None)
        if not handle:
            return
        info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        ok = kernel32.SetInformationJobObject(
            handle,
            JobObjectExtendedLimitInformation,
            ctypes.byref(info),
            ctypes.sizeof(info),
        )
        if not ok:
            kernel32.CloseHandle(handle)
            return
        self._handle = handle

    def assign(self, process) -> bool:
        if os.name != "nt" or not self._handle:
            return False
        raw_handle = getattr(process, "_handle", None)
        if raw_handle:
            return bool(kernel32.AssignProcessToJobObject(self._handle, int(raw_handle)))
        pid = getattr(process, "pid", None)
        if not pid:
            return False
        proc_handle = kernel32.OpenProcess(PROCESS_SET_QUOTA | PROCESS_TERMINATE, False, pid)
        if not proc_handle:
            return False
        try:
            return bool(kernel32.AssignProcessToJobObject(self._handle, proc_handle))
        finally:
            kernel32.CloseHandle(proc_handle)

    def terminate(self, exit_code: int = 1) -> bool:
        if os.name != "nt" or not self._handle:
            return False
        return bool(kernel32.TerminateJobObject(self._handle, exit_code))

    def close(self) -> None:
        if os.name == "nt" and self._handle:
            kernel32.CloseHandle(self._handle)
            self._handle = None


def _list_explorer_windows() -> list[tuple[int, str]]:
    windows: list[tuple[int, str]] = []
    cls_buf = ctypes.create_unicode_buffer(64)
    title_buf = ctypes.create_unicode_buffer(512)

    def callback(hwnd: int, _lparam: int) -> bool:
        if user32.IsWindowVisible(hwnd):
            if user32.GetClassNameW(hwnd, cls_buf, 64) and cls_buf.value == "CabinetWClass":
                user32.GetWindowTextW(hwnd, title_buf, 512)
                windows.append((hwnd, title_buf.value))
        return True

    user32.EnumWindows(WNDENUMPROC(callback), 0)
    return windows


def _bring_window_to_foreground(hwnd: int) -> None:
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)
    fg = user32.GetForegroundWindow()
    cur_tid = kernel32.GetCurrentThreadId()
    fg_tid = user32.GetWindowThreadProcessId(fg, None) if fg else 0
    target_tid = user32.GetWindowThreadProcessId(hwnd, None)
    attached_fg = bool(fg_tid and fg_tid != cur_tid and user32.AttachThreadInput(cur_tid, fg_tid, True))
    attached_target = bool(
        target_tid and target_tid != cur_tid and target_tid != fg_tid
        and user32.AttachThreadInput(cur_tid, target_tid, True)
    )
    try:
        user32.AllowSetForegroundWindow(ASFW_ANY)
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
    finally:
        if attached_target:
            user32.AttachThreadInput(cur_tid, target_tid, False)
        if attached_fg:
            user32.AttachThreadInput(cur_tid, fg_tid, False)


def open_folder_foreground(path: str) -> None:
    if os.name != "nt":
        raise OSError("仅 Windows 支持前台打开资源管理器")
    before = {hwnd for hwnd, _ in _list_explorer_windows()}
    user32.AllowSetForegroundWindow(ASFW_ANY)
    result = shell32.ShellExecuteW(None, "open", path, None, None, SW_SHOWNORMAL)
    if not result or int(result) <= 32:
        raise OSError(f"ShellExecuteW 打开目录失败（代码：{result}）")

    folder_name = os.path.basename(path.rstrip("\/")).casefold()
    deadline = time.monotonic() + 0.6
    reused_candidate: int | None = None
    while time.monotonic() < deadline:
        time.sleep(0.05)
        current = _list_explorer_windows()
        for hwnd, _title in current:
            if hwnd not in before:
                _bring_window_to_foreground(hwnd)
                return
        if reused_candidate is None and folder_name:
            for hwnd, title in current:
                if folder_name in title.casefold():
                    reused_candidate = hwnd
                    break
        if reused_candidate is not None and (deadline - time.monotonic()) < 0.35:
            _bring_window_to_foreground(reused_candidate)
            return
    if reused_candidate is not None:
        _bring_window_to_foreground(reused_candidate)


class SingleInstanceMutex:
    """Windows named mutex ensuring only one launcher instance runs per port."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._handle: int | None = None
        self.already_running = False
        if os.name != "nt":
            return
        handle = _kernel32_last_error.CreateMutexW(None, False, name)
        last_error = ctypes.get_last_error()
        if handle and last_error == ERROR_ALREADY_EXISTS:
            kernel32.CloseHandle(handle)
            self.already_running = True
        elif handle:
            self._handle = handle

    def release(self) -> None:
        if os.name == "nt" and self._handle:
            kernel32.CloseHandle(self._handle)
            self._handle = None
