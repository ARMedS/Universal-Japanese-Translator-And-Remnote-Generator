import unittest

import numpy as np

from ujt.capture import MARKER_RGB, MARKER_SIZE, find_marker_frames

M = MARKER_SIZE


def scene(width=1200, height=700, seed=1) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(0, 120, size=(height, width, 3), dtype=np.uint8)


def draw_frame(img: np.ndarray, x: int, y: int, w: int, h: int) -> None:
    for cx, cy in ((x, y), (x + w - M, y), (x, y + h - M), (x + w - M, y + h - M)):
        img[cy : cy + M, cx : cx + M] = MARKER_RGB


class MarkerTests(unittest.TestCase):
    def test_finds_exact_frame(self) -> None:
        img = scene()
        draw_frame(img, 40, 50, 500, 220)
        self.assertEqual(find_marker_frames(img, 500, 220, M), [(40, 50)])

    def test_stray_pink_above_does_not_shift_or_stretch(self) -> None:
        # The old bbox-of-clusters code grew to include this and cropped the wrong area.
        img = scene()
        draw_frame(img, 40, 300, 500, 220)
        img[20 : 20 + 60, 100 : 100 + 400] = MARKER_RGB  # big hot-pink banner above
        img[10 : 10 + M, 700 : 700 + M] = MARKER_RGB  # lone marker-sized square
        self.assertEqual(find_marker_frames(img, 500, 220, M), [(40, 300)])

    def test_stale_capture_markers_elsewhere_are_ignored(self) -> None:
        # A second, differently sized "frame" (e.g. an old capture shown in the Monitor).
        img = scene()
        draw_frame(img, 40, 50, 500, 220)
        draw_frame(img, 700, 100, 380, 400)
        self.assertEqual(find_marker_frames(img, 500, 220, M), [(40, 50)])

    def test_missing_marker_is_not_guessed(self) -> None:
        img = scene()
        draw_frame(img, 40, 50, 500, 220)
        img[50 + 220 - M : 50 + 220, 40 + 500 - M : 40 + 500] = 0
        self.assertEqual(find_marker_frames(img, 500, 220, M), [])

    def test_no_pink_at_all(self) -> None:
        self.assertEqual(find_marker_frames(scene(), 500, 220, M), [])

    def test_slightly_off_colour_still_matches(self) -> None:
        img = scene()
        draw_frame(img, 100, 100, 300, 200)
        r, g, b = MARKER_RGB
        img[100 : 100 + M, 100 : 100 + M] = (r - 10, g + 10, b - 10)
        self.assertEqual(find_marker_frames(img, 300, 200, M), [(100, 100)])


if __name__ == "__main__":
    unittest.main()
