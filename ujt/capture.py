"""Capture the area inside the capture frame (KDE Plasma, X11 or Wayland).

* **X11** - the frame's position is read from the X server itself
  (`x11.window_geometry`), the pixels come straight from the root window
  (`x11.grab_rect`, ~2 ms), and the interior is cropped by exact arithmetic.
  No markers are drawn, so the frame stays visually quiet.
* **Wayland** - windows have no global coordinates, so the frame draws four
  small pink corner markers; a Spectacle full-desktop shot is searched for a
  marker rectangle of exactly the frame's size. Unrelated pink on screen
  cannot shift or stretch the result, and failure is an error, never a guess.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PyQt6.QtCore import QBuffer, QIODevice
from PyQt6.QtGui import QGuiApplication, QImage
from PyQt6.QtWidgets import QWidget

from . import x11

HEADER_H = 50
BORDER_PX = 7
GRIP_H = 18  # resize-grip row under the interior while the chrome is visible
MARKER_RGB = (255, 0, 170)
MARKER_SIZE = BORDER_PX  # keep the markers entirely inside the cropped border
MARKER_TOL = 24


class CaptureError(Exception):
    pass


class SnipCancelled(CaptureError):
    pass


@dataclass(frozen=True)
class FrameSpec:
    """Where the capture frame is, in logical global pixels."""

    x: int
    y: int
    w: int
    h: int
    scale: float
    chrome_hidden: bool

    @classmethod
    def from_widget(cls, widget: QWidget, chrome_hidden: bool) -> "FrameSpec":
        top = widget.window()
        handle = top.windowHandle()
        geo = handle.geometry() if handle is not None else top.geometry()
        scale = float((handle.devicePixelRatio() if handle is not None else top.devicePixelRatioF()) or 1.0)
        x, y, w, h = geo.x(), geo.y(), geo.width(), geo.height()
        if _is_x11():
            truth = x11.window_geometry(int(top.winId()))
            if truth is not None:
                # X reports native pixels; FrameSpec is logical.
                x, y = int(round(truth[0] / scale)), int(round(truth[1] / scale))
                w, h = int(round(truth[2] / scale)), int(round(truth[3] / scale))
        return cls(x, y, w, h, scale, chrome_hidden)

    def px(self, logical: float) -> int:
        return int(round(logical * self.scale))

    @property
    def native_w(self) -> int:
        return self.px(self.w)

    @property
    def native_h(self) -> int:
        return self.px(self.h)

    @property
    def marker(self) -> int:
        return max(1, self.px(MARKER_SIZE))


# --------------------------------------------------------------------- frame


def capture_frame(spec: FrameSpec) -> bytes:
    """PNG of the frame interior. Safe to call from a worker thread."""
    if spec.native_w < 40 or spec.native_h < 40:
        raise CaptureError(f"capture frame is too small ({spec.w}x{spec.h})")

    if _is_x11():
        grabbed = x11.grab_rect(spec.px(spec.x), spec.px(spec.y), spec.native_w, spec.native_h)
        if grabbed is None or grabbed[0].shape[:2] != (spec.native_h, spec.native_w):
            raise CaptureError(
                "the capture frame is partly off the desktop or the X server refused the grab"
            )
        rgb, origin = grabbed[0], (0, 0)
    else:
        rgb, origin = _locate_in_full_shot(spec)

    return _crop_interior(rgb, origin, spec)


def needs_markers() -> bool:
    """Corner markers are only drawn where the frame cannot be located exactly."""
    return not _is_x11()


def _is_x11() -> bool:
    """Real X11 only. Qt under XWayland is also 'xcb', but its root window
    does not contain native Wayland windows, so grabbing it would be wrong."""
    if not QGuiApplication.platformName().lower().startswith("xcb"):
        return False
    if os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland" or os.environ.get("WAYLAND_DISPLAY"):
        return False
    return x11.available()


def _locate_in_full_shot(spec: FrameSpec) -> tuple[np.ndarray, tuple[int, int]]:
    image = QImage.fromData(_spectacle_full_png(), "PNG")
    if image.isNull():
        raise CaptureError("screenshot produced an unreadable image")
    rgb = qimage_to_rgb(image)
    hits = find_marker_frames(rgb, spec.native_w, spec.native_h, spec.marker)
    if not hits:
        raise CaptureError(
            "could not find the capture frame in the screenshot "
            "(is the frame visible on screen?)"
        )
    return rgb, hits[0]


def _crop_interior(rgb: np.ndarray, origin: tuple[int, int], spec: FrameSpec) -> bytes:
    left = spec.px(BORDER_PX)
    top = spec.px(BORDER_PX if spec.chrome_hidden else HEADER_H)
    right = spec.px(BORDER_PX)
    bottom = spec.px(BORDER_PX + (0 if spec.chrome_hidden else GRIP_H))
    x0, y0 = origin[0] + left, origin[1] + top
    x1, y1 = origin[0] + spec.native_w - right, origin[1] + spec.native_h - bottom
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(rgb.shape[1], x1), min(rgb.shape[0], y1)
    if x1 - x0 < 8 or y1 - y0 < 8:
        raise CaptureError(f"interior crop too small: {x1 - x0}x{y1 - y0}")
    return rgb_to_png(rgb[y0:y1, x0:x1])


# ------------------------------------------------------------------- markers


def _marker_mask(rgb: np.ndarray) -> np.ndarray:
    r, g, b = MARKER_RGB
    return (
        (np.abs(rgb[:, :, 0].astype(np.int16) - r) <= MARKER_TOL)
        & (np.abs(rgb[:, :, 1].astype(np.int16) - g) <= MARKER_TOL)
        & (np.abs(rgb[:, :, 2].astype(np.int16) - b) <= MARKER_TOL)
    )


def find_marker_frames(rgb: np.ndarray, w: int, h: int, m: int) -> list[tuple[int, int]]:
    """Top-left corners of every rectangle whose four corners are solid markers.

    Only rectangles of exactly (w, h) qualify, so unrelated pink on screen -
    however much of it - cannot stretch or shift the result.
    """
    mask = _marker_mask(rgb)
    if mask.sum() < 4 * m * m:
        return []
    solid = _solid_blocks(mask, m)
    if not solid.any():
        return []
    dx, dy = w - m, h - m
    rows, cols = solid.shape
    if dx >= cols or dy >= rows:
        return []
    anchor = solid[: rows - dy, : cols - dx]
    others = (
        _dilate(solid[: rows - dy, dx:])
        & _dilate(solid[dy:, : cols - dx])
        & _dilate(solid[dy:, dx:])
    )
    ys, xs = np.nonzero(anchor & others)
    hits = sorted(zip(xs.tolist(), ys.tolist()), key=lambda p: (p[1], p[0]))
    return _dedupe(hits)


def _solid_blocks(mask: np.ndarray, m: int) -> np.ndarray:
    """solid[y, x] is True where the m x m block starting at (y, x) is all set."""
    integral = np.zeros((mask.shape[0] + 1, mask.shape[1] + 1), dtype=np.int32)
    np.cumsum(np.cumsum(mask, axis=0, dtype=np.int32), axis=1, out=integral[1:, 1:])
    sums = integral[m:, m:] - integral[:-m, m:] - integral[m:, :-m] + integral[:-m, :-m]
    return sums == m * m


def _dilate(a: np.ndarray) -> np.ndarray:
    """3x3 binary dilation (tolerates fractional-scale rounding)."""
    out = a.copy()
    out[1:, :] |= a[:-1, :]
    out[:-1, :] |= a[1:, :]
    tmp = out.copy()
    out[:, 1:] |= tmp[:, :-1]
    out[:, :-1] |= tmp[:, 1:]
    return out


def _dedupe(hits: list[tuple[int, int]]) -> list[tuple[int, int]]:
    kept: list[tuple[int, int]] = []
    for x, y in hits:
        if all(abs(x - kx) > 2 or abs(y - ky) > 2 for kx, ky in kept):
            kept.append((x, y))
    return kept


# ----------------------------------------------------------------- image I/O


def qimage_to_rgb(image: QImage) -> np.ndarray:
    img = image.convertToFormat(QImage.Format.Format_RGB888)
    h, w, bpl = img.height(), img.width(), img.bytesPerLine()
    if w < 1 or h < 1:
        raise CaptureError("empty screenshot")
    raw = np.frombuffer(bytes(img.constBits().asarray(bpl * h)), dtype=np.uint8)
    return raw.reshape(h, bpl)[:, : w * 3].reshape(h, w, 3).copy()


def rgb_to_png(rgb: np.ndarray) -> bytes:
    rgb = np.ascontiguousarray(rgb)
    h, w, _ = rgb.shape
    image = QImage(rgb.data, w, h, w * 3, QImage.Format.Format_RGB888)
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    if not image.save(buf, "PNG"):
        raise CaptureError("failed to encode cropped PNG")
    return bytes(buf.data())


# ------------------------------------------------------------- spectacle use


def _spectacle_full_png() -> bytes:
    binary = shutil.which("spectacle")
    if not binary:
        raise CaptureError("spectacle is not installed (needed for Wayland capture)")
    tmp = Path(tempfile.mkdtemp(prefix="ujt-cap-"))
    try:
        out = tmp / "full.png"
        try:
            result = subprocess.run(
                [binary, "-f", "-b", "-n", "-o", str(out)],
                capture_output=True,
                check=False,
                timeout=30,
            )
        except subprocess.TimeoutExpired as exc:
            raise CaptureError("screenshot timed out") from exc
        if out.exists() and out.stat().st_size > 0:
            return out.read_bytes()
        err = result.stderr.decode("utf-8", errors="replace").strip()
        raise CaptureError(err or "spectacle produced no PNG")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def capture_snip() -> bytes:
    """Interactive rectangle picker (Spectacle). Blocks until the user finishes.

    Run this off the GUI thread. Raises SnipCancelled if the user backs out.
    """
    binary = shutil.which("spectacle")
    if not binary:
        raise CaptureError("spectacle is not installed")
    tmp = Path(tempfile.mkdtemp(prefix="ujt-snip-"))
    try:
        path = tmp / "snip.png"
        try:
            result = subprocess.run(
                [binary, "-r", "-b", "-n", "-o", str(path)],
                capture_output=True,
                check=False,
                timeout=120,
            )
        except subprocess.TimeoutExpired as exc:
            raise CaptureError("snip timed out after 2 minutes") from exc
        if path.exists() and path.stat().st_size > 0:
            return path.read_bytes()
        err = result.stderr.decode("utf-8", errors="replace").strip()
        if result.returncode == 0:
            raise SnipCancelled("snip cancelled")  # KDE apps print unrelated warnings to stderr
        raise CaptureError(err or f"spectacle exited with code {result.returncode}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
