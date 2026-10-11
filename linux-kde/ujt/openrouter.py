"""OpenRouter chat/completions — vision (image) and text-only flashcards."""

from __future__ import annotations

import base64
import json
import socket
from typing import Any

import requests
from requests.adapters import HTTPAdapter

API_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"


def force_ipv4() -> None:
    """Avoid IPv6 blackholes (the Windows NetworkHelper equivalent)."""
    original = socket.getaddrinfo

    def ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
        return original(host, port, socket.AF_INET, type, proto, flags)

    socket.getaddrinfo = ipv4_only


class OpenRouterError(Exception):
    pass


def _session() -> requests.Session:
    sess = requests.Session()
    sess.mount("https://", HTTPAdapter(max_retries=1))
    sess.mount("http://", HTTPAdapter(max_retries=1))
    return sess


def _content_from_response(data: dict[str, Any]) -> str:
    choices = data.get("choices") or []
    if not choices:
        raise OpenRouterError("OpenRouter returned no choices")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text") or "")
            elif isinstance(item, str):
                parts.append(item)
        return "".join(parts)
    raise OpenRouterError("OpenRouter response had no text content")


def translate_image(api_key: str, model: str, prompt: str, png_bytes: bytes, timeout: int = 120) -> str:
    if not api_key:
        raise OpenRouterError("OpenRouter API key is not set")
    b64 = base64.b64encode(png_bytes).decode("ascii")
    body = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": [{"type": "text", "text": prompt}],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"},
                    }
                ],
            },
        ],
    }
    return _post(api_key, body, timeout)


def complete_text(api_key: str, model: str, prompt: str, timeout: int = 120) -> str:
    if not api_key:
        raise OpenRouterError("OpenRouter API key is not set")
    body = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": [{"type": "text", "text": "You are a helpful assistant."}],
            },
            {
                "role": "user",
                "content": [{"type": "text", "text": prompt}],
            },
        ],
    }
    return _post(api_key, body, timeout)


def _post(api_key: str, body: dict[str, Any], timeout: int) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/ARMedS/Universal-Japanese-Translator-And-Remnote-Generator",
        "X-Title": "UJT-Linux",
    }
    try:
        response = _session().post(API_ENDPOINT, headers=headers, json=body, timeout=timeout)
    except requests.RequestException as exc:
        raise OpenRouterError(f"OpenRouter request failed: {exc}") from exc
    if response.status_code >= 400:
        raise OpenRouterError(f"OpenRouter {response.status_code}: {response.text[:800]}")
    try:
        data = response.json()
    except json.JSONDecodeError as exc:
        raise OpenRouterError(f"OpenRouter returned non-JSON: {response.text[:400]}") from exc
    return _content_from_response(data)
