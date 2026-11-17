"""Minimal ctypes bindings: taskbar discovery, maximized-window lookup, screen capture,
and the click-through backdrop window drawn behind the taskbar. Stdlib only."""
import ctypes
import winreg
from ctypes import wintypes as wt
from dataclasses import dataclass

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
dwmapi = ctypes.WinDLL("dwmapi")
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)
WNDENUMPROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

# --- constants -------------------------------------------------------------
GWL_STYLE, GWL_EXSTYLE = -16, -20
WS_POPUP = 0x80000000
WS_EX_TOPMOST, WS_EX_TRANSPARENT, WS_EX_TOOLWINDOW = 0x8, 0x20, 0x80
WS_EX_LAYERED, WS_EX_NOACTIVATE = 0x80000, 0x08000000
LWA_ALPHA = 0x2
SW_HIDE, SW_SHOWNOACTIVATE = 0, 4
SWP_NOACTIVATE, SWP_SHOWWINDOW = 0x10, 0x40
WM_DESTROY, WM_PAINT, WM_ERASEBKGND = 0x2, 0xF, 0x14
PM_REMOVE = 0x1
SRCCOPY = 0x00CC0020
DIB_RGB_COLORS = 0
DWMWA_CLOAKED = 14
MONITOR_DEFAULTTONULL = 0


class PAINTSTRUCT(ctypes.Structure):
    _fields_ = [("hdc", wt.HDC), ("fErase", wt.BOOL), ("rcPaint", wt.RECT),
                ("fRestore", wt.BOOL), ("fIncUpdate", wt.BOOL), ("rgbReserved", ctypes.c_byte * 32)]


class WNDCLASSW(ctypes.Structure):
    _fields_ = [("style", wt.UINT), ("lpfnWndProc", WNDPROC), ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int), ("hInstance", wt.HINSTANCE), ("hIcon", wt.HICON),
                ("hCursor", wt.HANDLE), ("hbrBackground", wt.HBRUSH),
                ("lpszMenuName", wt.LPCWSTR), ("lpszClassName", wt.LPCWSTR)]


class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wt.DWORD), ("rcMonitor", wt.RECT), ("rcWork", wt.RECT), ("dwFlags", wt.DWORD)]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wt.DWORD), ("biWidth", wt.LONG), ("biHeight", wt.LONG),
                ("biPlanes", wt.WORD), ("biBitCount", wt.WORD), ("biCompression", wt.DWORD),
                ("biSizeImage", wt.DWORD), ("biXPelsPerMeter", wt.LONG), ("biYPelsPerMeter", wt.LONG),
                ("biClrUsed", wt.DWORD), ("biClrImportant", wt.DWORD)]


def _proto(fn, restype, *argtypes):
    fn.restype, fn.argtypes = restype, list(argtypes)


_proto(user32.EnumWindows, wt.BOOL, WNDENUMPROC, wt.LPARAM)
_proto(user32.GetClassNameW, ctypes.c_int, wt.HWND, wt.LPWSTR, ctypes.c_int)
_proto(user32.GetWindowTextW, ctypes.c_int, wt.HWND, wt.LPWSTR, ctypes.c_int)
_proto(user32.IsWindowVisible, wt.BOOL, wt.HWND)
_proto(user32.IsZoomed, wt.BOOL, wt.HWND)
_proto(user32.IsIconic, wt.BOOL, wt.HWND)
_proto(user32.GetWindowRect, wt.BOOL, wt.HWND, ctypes.POINTER(wt.RECT))
_proto(user32.GetWindowLongPtrW, ctypes.c_ssize_t, wt.HWND, ctypes.c_int)
_proto(user32.MonitorFromWindow, wt.HMONITOR, wt.HWND, wt.DWORD)
_proto(user32.GetMonitorInfoW, wt.BOOL, wt.HMONITOR, ctypes.POINTER(MONITORINFO))
_proto(user32.GetDC, wt.HDC, wt.HWND)
_proto(user32.ReleaseDC, ctypes.c_int, wt.HWND, wt.HDC)
_proto(user32.RegisterClassW, wt.ATOM, ctypes.POINTER(WNDCLASSW))
_proto(user32.CreateWindowExW, wt.HWND, wt.DWORD, wt.LPCWSTR, wt.LPCWSTR, wt.DWORD,
       ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.HWND, wt.HMENU, wt.HINSTANCE, wt.LPVOID)
_proto(user32.DestroyWindow, wt.BOOL, wt.HWND)
_proto(user32.DefWindowProcW, LRESULT, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)
_proto(user32.SetLayeredWindowAttributes, wt.BOOL, wt.HWND, wt.COLORREF, wt.BYTE, wt.DWORD)
_proto(user32.SetWindowPos, wt.BOOL, wt.HWND, wt.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.UINT)
_proto(user32.ShowWindow, wt.BOOL, wt.HWND, ctypes.c_int)
_proto(user32.InvalidateRect, wt.BOOL, wt.HWND, ctypes.POINTER(wt.RECT), wt.BOOL)
_proto(user32.UpdateWindow, wt.BOOL, wt.HWND)
_proto(user32.BeginPaint, wt.HDC, wt.HWND, ctypes.POINTER(PAINTSTRUCT))
_proto(user32.EndPaint, wt.BOOL, wt.HWND, ctypes.POINTER(PAINTSTRUCT))
_proto(user32.FillRect, ctypes.c_int, wt.HDC, ctypes.POINTER(wt.RECT), wt.HBRUSH)
_proto(user32.GetClientRect, wt.BOOL, wt.HWND, ctypes.POINTER(wt.RECT))
_proto(user32.PeekMessageW, wt.BOOL, ctypes.POINTER(wt.MSG), wt.HWND, wt.UINT, wt.UINT, wt.UINT)
_proto(user32.TranslateMessage, wt.BOOL, ctypes.POINTER(wt.MSG))
_proto(user32.DispatchMessageW, LRESULT, ctypes.POINTER(wt.MSG))
_proto(user32.SetProcessDpiAwarenessContext, wt.BOOL, wt.HANDLE)
_proto(gdi32.CreateCompatibleDC, wt.HDC, wt.HDC)
_proto(gdi32.CreateCompatibleBitmap, wt.HBITMAP, wt.HDC, ctypes.c_int, ctypes.c_int)
_proto(gdi32.SelectObject, wt.HGDIOBJ, wt.HDC, wt.HGDIOBJ)
_proto(gdi32.BitBlt, wt.BOOL, wt.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
       wt.HDC, ctypes.c_int, ctypes.c_int, wt.DWORD)
_proto(gdi32.GetDIBits, ctypes.c_int, wt.HDC, wt.HBITMAP, wt.UINT, wt.UINT, wt.LPVOID,
       ctypes.POINTER(BITMAPINFOHEADER), wt.UINT)
_proto(gdi32.DeleteObject, wt.BOOL, wt.HGDIOBJ)
_proto(gdi32.DeleteDC, wt.BOOL, wt.HDC)
_proto(gdi32.CreateSolidBrush, wt.HBRUSH, wt.COLORREF)
_proto(dwmapi.DwmGetWindowAttribute, ctypes.c_long, wt.HWND, wt.DWORD, wt.LPVOID, wt.DWORD)
_proto(kernel32.GetModuleHandleW, wt.HMODULE, wt.LPCWSTR)


def make_dpi_aware() -> None:
    """Work in physical pixels so rects and captures line up on scaled displays."""
    user32.SetProcessDpiAwarenessContext(wt.HANDLE(-4))  # PER_MONITOR_AWARE_V2


# --- window queries --------------------------------------------------------
def class_name(hwnd) -> str:
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def window_title(hwnd) -> str:
    buf = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(hwnd, buf, 256)
    return buf.value


def window_rect(hwnd) -> wt.RECT:
    r = wt.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return r


def is_cloaked(hwnd) -> bool:
    v = wt.DWORD()
    return dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, ctypes.byref(v), 4) == 0 and v.value != 0


def windows_in_z_order() -> list[int]:
    """Top-level windows, topmost first."""
    out: list[int] = []
    cb = WNDENUMPROC(lambda h, _: out.append(h) or True)
    user32.EnumWindows(cb, 0)
    return out


@dataclass
class Monitor:
    handle: int
    rect: tuple[int, int, int, int]   # left, top, right, bottom
    work: tuple[int, int, int, int]


def monitor_of(hwnd) -> Monitor | None:
    hmon = user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONULL)
    if not hmon:
        return None
    mi = MONITORINFO(cbSize=ctypes.sizeof(MONITORINFO))
    user32.GetMonitorInfoW(hmon, ctypes.byref(mi))
    m, w = mi.rcMonitor, mi.rcWork
    return Monitor(hmon, (m.left, m.top, m.right, m.bottom), (w.left, w.top, w.right, w.bottom))


@dataclass
class Taskbar:
    hwnd: int
    rect: tuple[int, int, int, int]
    monitor: Monitor
    edge: str  # "bottom" | "top" | "left" | "right"


def find_taskbars() -> list[Taskbar]:
    bars = []
    for h in windows_in_z_order():
        if class_name(h) not in ("Shell_TrayWnd", "Shell_SecondaryTrayWnd") or not user32.IsWindowVisible(h):
            continue
        mon = monitor_of(h)
        if mon is None:
            continue
        r = window_rect(h)
        # Clip to the monitor (an auto-hidden bar sits mostly off-screen).
        rect = (max(r.left, mon.rect[0]), max(r.top, mon.rect[1]),
                min(r.right, mon.rect[2]), min(r.bottom, mon.rect[3]))
        if rect[2] - rect[0] < 8 or rect[3] - rect[1] < 8:
            continue
        w, hgt = rect[2] - rect[0], rect[3] - rect[1]
        if w >= hgt:
            edge = "bottom" if rect[3] == mon.rect[3] else "top"
        else:
            edge = "right" if rect[2] == mon.rect[2] else "left"
        bars.append(Taskbar(h, rect, mon, edge))
    return bars


_SKIP_CLASSES = {"Shell_TrayWnd", "Shell_SecondaryTrayWnd", "Progman", "WorkerW", "TaskbarMatchBackdrop"}


def maximized_window_on(monitor: Monitor) -> int | None:
    """Topmost visible, uncloaked, maximized app window on this monitor, if any."""
    for h in windows_in_z_order():
        if not user32.IsWindowVisible(h) or user32.IsIconic(h) or not user32.IsZoomed(h):
            continue
        if user32.GetWindowLongPtrW(h, GWL_EXSTYLE) & WS_EX_TOOLWINDOW:
            continue
        if class_name(h) in _SKIP_CLASSES or is_cloaked(h):
            continue
        mon = monitor_of(h)
        if mon and mon.handle == monitor.handle:
            return h
    return None


def sample_strip(bar: Taskbar, rows: int = 3, gap: int = 1) -> tuple[tuple[int, int, int, int], list]:
    """Rect of the app pixels right next to the taskbar, and those pixels as (r,g,b)."""
    l, t, r, b = bar.rect
    if bar.edge == "bottom":
        rect = (l, t - gap - rows, r, t - gap)
    elif bar.edge == "top":
        rect = (l, b + gap, r, b + gap + rows)
    elif bar.edge == "left":
        rect = (r + gap, t, r + gap + rows, b)
    else:
        rect = (l - gap - rows, t, l - gap, b)
    return rect, capture(rect)


def capture(rect, step: int = 2) -> list[tuple[int, int, int]]:
    """Grab screen pixels in rect (every `step`th pixel along each row) as RGB tuples."""
    raw, w, h = capture_raw(rect)
    px = []
    for y in range(h):
        row = y * w * 4
        for x in range(0, w, step):
            i = row + x * 4
            px.append((raw[i + 2], raw[i + 1], raw[i]))  # BGRA -> RGB
    return px


def capture_raw(rect) -> tuple[bytes, int, int]:
    """Screen pixels in rect as top-down BGRA bytes."""
    l, t, r, b = rect
    w, h = r - l, b - t
    screen = user32.GetDC(None)
    mem = gdi32.CreateCompatibleDC(screen)
    bmp = gdi32.CreateCompatibleBitmap(screen, w, h)
    old = gdi32.SelectObject(mem, bmp)
    try:
        gdi32.BitBlt(mem, 0, 0, w, h, screen, l, t, SRCCOPY)
        bih = BITMAPINFOHEADER(biSize=ctypes.sizeof(BITMAPINFOHEADER), biWidth=w, biHeight=-h,
                               biPlanes=1, biBitCount=32, biCompression=0)
        buf = ctypes.create_string_buffer(w * h * 4)
        gdi32.GetDIBits(mem, bmp, 0, h, buf, ctypes.byref(bih), DIB_RGB_COLORS)
        return buf.raw, w, h
    finally:
        gdi32.SelectObject(mem, old)
        gdi32.DeleteObject(bmp)
        gdi32.DeleteDC(mem)
        user32.ReleaseDC(None, screen)


def taskbar_uses_light_text() -> bool:
    """Taskbar icons/clock are white when the *system* (not app) theme is dark."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as k:
            return winreg.QueryValueEx(k, "SystemUsesLightTheme")[0] == 0
    except OSError:
        return True


# --- backdrop window -------------------------------------------------------
class Backdrop:
    """A click-through, never-focused solid-color window kept directly *below* the
    taskbar in z-order. A transparent taskbar shows it instead of the wallpaper."""

    _class_registered = False
    _instances: dict[int, "Backdrop"] = {}  # hwnd -> instance, for the shared window proc

    @staticmethod
    def _wndproc(hwnd, msg, wparam, lparam):
        if msg == WM_ERASEBKGND:
            return 1
        if msg == WM_PAINT and hwnd in Backdrop._instances:
            ps = PAINTSTRUCT()
            hdc = user32.BeginPaint(hwnd, ctypes.byref(ps))
            Backdrop._instances[hwnd]._paint(hdc)
            user32.EndPaint(hwnd, ctypes.byref(ps))
            return 0
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _paint(self, hdc) -> None:
        rc = wt.RECT()
        user32.GetClientRect(self.hwnd, ctypes.byref(rc))
        _fill(hdc, rc, self._color or (0, 0, 0))
        if self._line and self.line_width > 0:
            # Divider on the edge that touches the app.
            w = self.line_width
            line = wt.RECT(rc.left, rc.top, rc.right, rc.bottom)
            if self.edge == "bottom":
                line.bottom = rc.top + w
            elif self.edge == "top":
                line.top = rc.bottom - w
            elif self.edge == "left":
                line.left = rc.right - w
            else:
                line.right = rc.left + w
            _fill(hdc, line, self._line)

    _proc_ref = WNDPROC(lambda *a: Backdrop._wndproc(*a))  # must outlive every window

    def __init__(self, line_width: int = 0):
        hinst = kernel32.GetModuleHandleW(None)
        if not Backdrop._class_registered:
            wc = WNDCLASSW(lpfnWndProc=Backdrop._proc_ref, hInstance=hinst,
                           lpszClassName="TaskbarMatchBackdrop")
            user32.RegisterClassW(ctypes.byref(wc))
            Backdrop._class_registered = True
        ex = WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE | WS_EX_TOPMOST
        self.hwnd = user32.CreateWindowExW(ex, "TaskbarMatchBackdrop", "TaskbarMatch backdrop", WS_POPUP,
                                           0, 0, 1, 1, None, None, hinst, None)
        if not self.hwnd:
            raise ctypes.WinError(ctypes.get_last_error())
        self.visible = False
        self._alpha = -1
        self._color: tuple[int, int, int] | None = None
        self._line: tuple[int, int, int] | None = None
        self.line_width = line_width
        self.edge = "bottom"
        Backdrop._instances[self.hwnd] = self

    def set_color(self, rgb: tuple[int, int, int], line: tuple[int, int, int] | None = None) -> None:
        if rgb != self._color or line != self._line:
            self._color, self._line = rgb, line
            user32.InvalidateRect(self.hwnd, None, False)

    def set_alpha(self, alpha: int) -> None:
        if alpha != self._alpha:
            self._alpha = alpha
            user32.SetLayeredWindowAttributes(self.hwnd, 0, alpha, LWA_ALPHA)

    def place_under(self, bar: Taskbar) -> None:
        l, t, r, b = bar.rect
        if bar.edge != self.edge:
            self.edge = bar.edge
            user32.InvalidateRect(self.hwnd, None, False)
        # Inserting after the (topmost) taskbar puts us right beneath it, above normal windows.
        user32.SetWindowPos(self.hwnd, bar.hwnd, l, t, r - l, b - t, SWP_NOACTIVATE | SWP_SHOWWINDOW)
        if not self.visible:
            user32.ShowWindow(self.hwnd, SW_SHOWNOACTIVATE)
            self.visible = True

    def hide(self) -> None:
        if self.visible:
            user32.ShowWindow(self.hwnd, SW_HIDE)
            self.visible = False

    def destroy(self) -> None:
        Backdrop._instances.pop(self.hwnd, None)
        user32.DestroyWindow(self.hwnd)


def _fill(hdc, rect: wt.RECT, rgb: tuple[int, int, int]) -> None:
    brush = gdi32.CreateSolidBrush(rgb[0] | (rgb[1] << 8) | (rgb[2] << 16))
    user32.FillRect(hdc, ctypes.byref(rect), brush)
    gdi32.DeleteObject(brush)


def pump_messages() -> None:
    msg = wt.MSG()
    while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, PM_REMOVE):
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))
