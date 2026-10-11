"""XDG config, keys.env, and window geometry — never store API keys in JSON."""

from __future__ import annotations

import json
import os
import shutil
import stat
from pathlib import Path
from typing import Any

LINUX_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = LINUX_ROOT.parent
BUNDLED_PROMPTS = LINUX_ROOT / "prompts"
KANJI_CSV = PROJECT_ROOT / "components-kc.csv"
ICON_PATH = PROJECT_ROOT / "media" / "Icon1.ico"

APP_ID = os.environ.get("UJT_CONFIG_ID", "ujt-kde")
CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / APP_ID
CONFIG_PATH = CONFIG_DIR / "config.json"
KEYS_PATH = CONFIG_DIR / "keys.env"
PROMPT_PATH = CONFIG_DIR / "prompt.txt"
FLASHCARD_PROMPT_PATH = CONFIG_DIR / "flashcard_prompt.txt"

DEFAULT_VISION_MODEL = "google/gemini-3.1-flash-lite"
DEFAULT_FLASHCARD_MODEL = "google/gemini-3.1-flash-lite"
MODEL_CHOICES = [
    "google/gemini-3.1-flash-lite",
    "google/gemini-2.5-flash-preview-09-2025",
    "google/gemini-pro-vision",
    "openai/gpt-4o",
    "anthropic/claude-3-haiku",
]

DEFAULTS: dict[str, Any] = {
    "openrouter_model": DEFAULT_VISION_MODEL,
    "openrouter_flashcard_model": DEFAULT_FLASHCARD_MODEL,
    "game_name": "Bunny Girl Academy",
    "source_language": "ja",
    "target_language": "en",
    "border_opacity": 1.0,
    "chatbox_font_size": 32,
    "windows": {},
}


def ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not PROMPT_PATH.exists():
        src = BUNDLED_PROMPTS / "prompt.txt"
        if src.exists():
            shutil.copyfile(src, PROMPT_PATH)
    if not FLASHCARD_PROMPT_PATH.exists():
        src = BUNDLED_PROMPTS / "flashcard_prompt.txt"
        if src.exists():
            shutil.copyfile(src, FLASHCARD_PROMPT_PATH)


def _read_json() -> dict[str, Any]:
    ensure_config_dir()
    if not CONFIG_PATH.exists():
        return dict(DEFAULTS)
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(DEFAULTS)
    merged = dict(DEFAULTS)
    merged.update(data)
    if "windows" not in merged or not isinstance(merged["windows"], dict):
        merged["windows"] = {}
    return merged


def _write_json(data: dict[str, Any]) -> None:
    ensure_config_dir()
    tmp = CONFIG_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(CONFIG_PATH)


class Config:
    def __init__(self) -> None:
        self._data = _read_json()

    def save(self) -> None:
        _write_json(self._data)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self.save()

    @property
    def vision_model(self) -> str:
        return str(self._data.get("openrouter_model") or DEFAULT_VISION_MODEL)

    @vision_model.setter
    def vision_model(self, value: str) -> None:
        self.set("openrouter_model", value.strip())

    @property
    def flashcard_model(self) -> str:
        return str(self._data.get("openrouter_flashcard_model") or DEFAULT_FLASHCARD_MODEL)

    @flashcard_model.setter
    def flashcard_model(self, value: str) -> None:
        self.set("openrouter_flashcard_model", value.strip())

    @property
    def game_name(self) -> str:
        return str(self._data.get("game_name") or "")

    @game_name.setter
    def game_name(self, value: str) -> None:
        self.set("game_name", value)

    @property
    def source_language(self) -> str:
        return str(self._data.get("source_language") or "ja")

    @source_language.setter
    def source_language(self, value: str) -> None:
        self.set("source_language", value)

    @property
    def target_language(self) -> str:
        return str(self._data.get("target_language") or "en")

    @target_language.setter
    def target_language(self, value: str) -> None:
        self.set("target_language", value)

    @property
    def border_opacity(self) -> float:
        try:
            return float(self._data.get("border_opacity", 1.0))
        except (TypeError, ValueError):
            return 1.0

    @border_opacity.setter
    def border_opacity(self, value: float) -> None:
        self.set("border_opacity", max(0.05, min(1.0, float(value))))

    def window(self, name: str) -> dict[str, Any] | None:
        geo = self._data.get("windows", {}).get(name)
        return geo if isinstance(geo, dict) else None

    def set_window(
        self,
        name: str,
        x: int,
        y: int,
        w: int,
        h: int,
        visible: bool,
        screen: str = "",
    ) -> None:
        windows = self._data.setdefault("windows", {})
        windows[name] = {
            "x": int(x),
            "y": int(y),
            "w": int(w),
            "h": int(h),
            "visible": bool(visible),
            "screen": screen,
        }
        self.save()

    def load_prompt(self) -> str:
        ensure_config_dir()
        if PROMPT_PATH.exists():
            return PROMPT_PATH.read_text(encoding="utf-8").strip()
        bundled = BUNDLED_PROMPTS / "prompt.txt"
        return bundled.read_text(encoding="utf-8").strip() if bundled.exists() else ""

    def save_prompt(self, text: str) -> None:
        ensure_config_dir()
        PROMPT_PATH.write_text(text.strip() + "\n", encoding="utf-8")

    def load_flashcard_prompt(self) -> str:
        ensure_config_dir()
        if FLASHCARD_PROMPT_PATH.exists():
            return FLASHCARD_PROMPT_PATH.read_text(encoding="utf-8").strip()
        bundled = BUNDLED_PROMPTS / "flashcard_prompt.txt"
        return bundled.read_text(encoding="utf-8").strip() if bundled.exists() else ""

    def save_flashcard_prompt(self, text: str) -> None:
        ensure_config_dir()
        FLASHCARD_PROMPT_PATH.write_text(text.strip() + "\n", encoding="utf-8")

    def api_key(self) -> str:
        env = os.environ.get("OPENROUTER_API_KEY", "").strip()
        if env:
            return env
        ensure_config_dir()
        if not KEYS_PATH.exists():
            return ""
        for line in KEYS_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            if key.strip() == "OPENROUTER_API_KEY":
                return value.strip().strip("'").strip('"')
        return ""

    def save_api_key(self, key: str) -> None:
        ensure_config_dir()
        existing: dict[str, str] = {}
        if KEYS_PATH.exists():
            for line in KEYS_PATH.read_text(encoding="utf-8").splitlines():
                if not line.strip() or line.strip().startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                existing[k.strip()] = v.strip()
        existing["OPENROUTER_API_KEY"] = key.strip()
        body = "".join(f"{k}={v}\n" for k, v in existing.items())
        KEYS_PATH.write_text(body, encoding="utf-8")
        KEYS_PATH.chmod(stat.S_IRUSR | stat.S_IWUSR)
        os.environ["OPENROUTER_API_KEY"] = key.strip()
