"""Thin ctypes bindings to libX11 (no extra dependency).

* `grab_rect` reads pixels straight from the X root window - ~2 ms for a
  window-sized region, identical to Spectacle's output, correct across
  monitors.  (`QScreen.grabWindow(0, ...)` was measured to return black or
  wrong regions depending on which screen it is called on.)
* `set_above` asks the window manager for _NET_WM_STATE_ABOVE the EWMH way,
  with no subprocess.

Every call opens its own Display connection, so it is safe from any thread.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import os

import numpy as np

_SUBSTRUCTURE_NOTIFY = 1 << 19
_SUBSTRUCTURE_REDIRECT = 1 << 20
_CLIENT_MESSAGE = 33
_ZPIXMAP = 2
_ALL_PLANES = 0xFFFFFFFF
_NET_WM_STATE_REMOVE = 0
_NET_WM_STATE_ADD = 1


class _XImage(ctypes.Structure):
    _fields_ = [
        ("width", ctypes.c_int),
        ("height", ctypes.c_int),
        ("xoffset", ctypes.c_int),
        ("format", ctypes.c_int),
        ("data", ctypes.POINTER(ctypes.c_char)),
        ("byte_order", ctypes.c_int),
        ("bitmap_unit", ctypes.c_int),
        ("bitmap_bit_order", ctypes.c_int),
        ("bitmap_pad", ctypes.c_int),
        ("depth", ctypes.c_int),
        ("bytes_per_line", ctypes.c_int),
        ("bits_per_pixel", ctypes.c_int),
        ("red_mask", ctypes.c_ulong),
        ("green_mask", ctypes.c_ulong),
        ("blue_mask", ctypes.c_ulong),
    ]


class _ClientMessage(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_int),
        ("serial", ctypes.c_ulong),
        ("send_event", ctypes.c_int),
        ("display", ctypes.c_void_p),
        ("window", ctypes.c_ulong),
        ("message_type", ctypes.c_ulong),
        ("format", ctypes.c_int),
        ("data", ctypes.c_long * 5),
    ]


class _XEvent(ctypes.Union):
    _fields_ = [("xclient", _ClientMessage), ("pad", ctypes.c_long * 24)]


_lib: ctypes.CDLL | None = None


def _load() -> ctypes.CDLL | None:
    global _lib
    if _lib is not None:
        return _lib
    name = ctypes.util.find_library("X11")
    if not name:
        return None
    lib = ctypes.CDLL(name)
    lib.XOpenDisplay.restype = ctypes.c_void_p
    lib.XOpenDisplay.argtypes = [ctypes.c_char_p]
    lib.XCloseDisplay.argtypes = [ctypes.c_void_p]
    lib.XDefaultRootWindow.restype = ctypes.c_ulong
    lib.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
    lib.XDefaultScreen.argtypes = [ctypes.c_void_p]
    lib.XDisplayWidth.argtypes = [ctypes.c_void_p, ctypes.c_int]
    lib.XDisplayHeight.argtypes = [ctypes.c_void_p, ctypes.c_int]
    lib.XInternAtom.restype = ctypes.c_ulong
    lib.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
    lib.XSendEvent.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_long, ctypes.c_void_p]
    lib.XFlush.argtypes = [ctypes.c_void_p]
    lib.XTranslateCoordinates.argtypes = [
        ctypes.c_void_p,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_ulong),
    ]
    lib.XGetGeometry.argtypes = [
        ctypes.c_void_p,
        ctypes.c_ulong,
        ctypes.POINTER(ctypes.c_ulong),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_uint),
        ctypes.POINTER(ctypes.c_uint),
        ctypes.POINTER(ctypes.c_uint),
        ctypes.POINTER(ctypes.c_uint),
    ]
    lib.XGetImage.restype = ctypes.POINTER(_XImage)
    lib.XGetImage.argtypes = [
        ctypes.c_void_p,
        ctypes.c_ulong,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_uint,
        ctypes.c_uint,
        ctypes.c_ulong,
        ctypes.c_int,
    ]
    _lib = lib
    return lib


def available() -> bool:
    return bool(os.environ.get("DISPLAY")) and _load() is not None


def root_size() -> tuple[int, int] | None:
    lib = _load()
    if lib is None:
        return None
    dpy = lib.XOpenDisplay(None)
    if not dpy:
        return None
    try:
        screen = lib.XDefaultScreen(dpy)
        return int(lib.XDisplayWidth(dpy, screen)), int(lib.XDisplayHeight(dpy, screen))
    finally:
        lib.XCloseDisplay(dpy)


def window_geometry(window_id: int) -> tuple[int, int, int, int] | None:
    """(x, y, w, h) of a window's client area in root coordinates, per the X server.

    This is the ground truth for where the window's pixels are, whatever
    reparenting or decoration the window manager does.
    """
    lib = _load()
    if lib is None or window_id == 0:
        return None
    dpy = lib.XOpenDisplay(None)
    if not dpy:
        return None
    try:
        root = lib.XDefaultRootWindow(dpy)
        rx, ry, child = ctypes.c_int(), ctypes.c_int(), ctypes.c_ulong()
        if not lib.XTranslateCoordinates(
            dpy, window_id, root, 0, 0, ctypes.byref(rx), ctypes.byref(ry), ctypes.byref(child)
        ):
            return None
        junk_win = ctypes.c_ulong()
        jx, jy = ctypes.c_int(), ctypes.c_int()
        w, h, border, depth = ctypes.c_uint(), ctypes.c_uint(), ctypes.c_uint(), ctypes.c_uint()
        if not lib.XGetGeometry(
            dpy,
            window_id,
            ctypes.byref(junk_win),
            ctypes.byref(jx),
            ctypes.byref(jy),
            ctypes.byref(w),
            ctypes.byref(h),
            ctypes.byref(border),
            ctypes.byref(depth),
        ):
            return None
        return rx.value, ry.value, int(w.value), int(h.value)
    finally:
        lib.XCloseDisplay(dpy)


def grab_rect(x: int, y: int, w: int, h: int) -> tuple[np.ndarray, int, int] | None:
    """RGB pixels of a root-window rectangle, clamped to the desktop.

    Returns (array[h, w, 3], actual_x, actual_y) or None if X is unreachable.
    The returned origin may differ from (x, y) when the request hangs off the
    desktop edge.
    """
    lib = _load()
    if lib is None:
        return None
    dpy = lib.XOpenDisplay(None)
    if not dpy:
        return None
    try:
        screen = lib.XDefaultScreen(dpy)
        max_w, max_h = int(lib.XDisplayWidth(dpy, screen)), int(lib.XDisplayHeight(dpy, screen))
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(max_w, x + w), min(max_h, y + h)
        if x1 <= x0 or y1 <= y0:
            return None
        root = lib.XDefaultRootWindow(dpy)
        img = lib.XGetImage(dpy, root, x0, y0, x1 - x0, y1 - y0, _ALL_PLANES, _ZPIXMAP)
        if not img:
            return None
        im = img.contents
        width, height, stride, bpp = im.width, im.height, im.bytes_per_line, im.bits_per_pixel
        try:
            if bpp != 32:
                return None
            raw = ctypes.string_at(im.data, stride * height)
        finally:
            # XDestroyImage is a macro in Xlib.h but also an exported function.
            destroy = lib.XDestroyImage
            destroy.argtypes = [ctypes.c_void_p]
            destroy(ctypes.cast(img, ctypes.c_void_p))
        pixels = np.frombuffer(raw, dtype=np.uint8).reshape(height, stride)
        bgrx = pixels[:, : width * 4].reshape(height, width, 4)
        return bgrx[:, :, [2, 1, 0]].copy(), x0, y0
    finally:
        lib.XCloseDisplay(dpy)


def set_above(window_id: int, above: bool) -> bool:
    """Ask the window manager to add/remove _NET_WM_STATE_ABOVE."""
    lib = _load()
    if lib is None or window_id == 0:
        return False
    dpy = lib.XOpenDisplay(None)
    if not dpy:
        return False
    try:
        root = lib.XDefaultRootWindow(dpy)
        event = _XEvent()
        msg = event.xclient
        msg.type = _CLIENT_MESSAGE
        msg.send_event = 1
        msg.display = dpy
        msg.window = window_id
        msg.message_type = lib.XInternAtom(dpy, b"_NET_WM_STATE", 0)
        msg.format = 32
        msg.data[0] = _NET_WM_STATE_ADD if above else _NET_WM_STATE_REMOVE
        msg.data[1] = lib.XInternAtom(dpy, b"_NET_WM_STATE_ABOVE", 0)
        msg.data[2] = 0
        msg.data[3] = 1  # source indication: normal application
        lib.XSendEvent(
            dpy, root, 0, _SUBSTRUCTURE_REDIRECT | _SUBSTRUCTURE_NOTIFY, ctypes.byref(event)
        )
        lib.XFlush(dpy)
        return True
    finally:
        lib.XCloseDisplay(dpy)
