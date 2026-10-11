"""Parse the vision-model JSON: {japanese, chunks:[{jp,en,romaji}]}."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field


@dataclass
class Chunk:
    jp: str
    en: str
    romaji: str = ""
    flashcard_created: bool = False
    cycle: int = 0  # 0 jp, 1 +en, 2 +en/romaji


@dataclass
class Translation:
    japanese: str
    chunks: list[Chunk] = field(default_factory=list)


class ParseError(Exception):
    pass


def parse_translation(text: str) -> Translation:
    blob = _extract_json_object(text)
    try:
        data = json.loads(blob)
    except json.JSONDecodeError as exc:
        raise ParseError(f"could not parse translation JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ParseError("translation JSON is not an object")
    japanese = str(data.get("japanese") or "").strip()
    raw_chunks = data.get("chunks") or []
    chunks: list[Chunk] = []
    if isinstance(raw_chunks, list):
        for item in raw_chunks:
            if not isinstance(item, dict):
                continue
            jp = str(item.get("jp") or "").strip()
            en = str(item.get("en") or "").strip()
            romaji = str(item.get("romaji") or "").strip()
            if jp:
                chunks.append(Chunk(jp=jp, en=en, romaji=romaji))
    if not japanese and not chunks:
        raise ParseError("JSON had no japanese text and no chunks")
    return Translation(japanese=japanese, chunks=chunks)


def _extract_json_object(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ParseError("no JSON object in model response")
    return cleaned[start : end + 1]
