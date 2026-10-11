"""Kanji → radical list from components-kc.csv."""

from __future__ import annotations

from pathlib import Path

from .config import KANJI_CSV


class RadicalIndex:
    def __init__(self, csv_path: Path | None = None) -> None:
        self._map: dict[str, list[str]] = {}
        path = csv_path or KANJI_CSV
        if path.exists():
            self._load(path)

    def _load(self, path: Path) -> None:
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split(",") if p.strip()]
            if len(parts) < 2:
                continue
            kanji, radicals = parts[0], parts[1:]
            if kanji:
                self._map[kanji] = radicals

    def format_for_prompt(self, japanese: str) -> str:
        pieces: list[str] = []
        seen: set[str] = set()
        for ch in japanese:
            if ch in seen:
                continue
            radicals = self._map.get(ch)
            if not radicals:
                continue
            seen.add(ch)
            pieces.append(f"{ch}({''.join(radicals)})")
        return ", ".join(pieces)
