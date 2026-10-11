"""Single-instance Unix socket: a second launch raises the running app."""

from __future__ import annotations

import os
import socket
from collections.abc import Callable
from pathlib import Path

from PyQt6.QtCore import QObject, QSocketNotifier

# Namespaced by edition so the COSMIC and KDE builds never steal each other's socket.
_EDITION = os.environ.get("UJT_CONFIG_ID", "ujt-kde")
SOCK_PATH = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp")) / f"{_EDITION}.sock"


def send_command(command: str, timeout: float = 0.4) -> bool:
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect(str(SOCK_PATH))
        sock.sendall(command.encode("utf-8") + b"\n")
        sock.close()
        return True
    except OSError:
        return False


class CommandServer(QObject):
    def __init__(self, parent: QObject, on_command: Callable[[str], None]) -> None:
        super().__init__(parent)
        self._on_command = on_command
        if SOCK_PATH.exists():
            try:
                SOCK_PATH.unlink()
            except OSError as exc:
                raise RuntimeError(f"could not replace {SOCK_PATH}: {exc}") from exc
        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._sock.bind(str(SOCK_PATH))
        self._sock.listen(4)
        self._sock.setblocking(False)
        self._notifier = QSocketNotifier(self._sock.fileno(), QSocketNotifier.Type.Read, self)
        self._notifier.activated.connect(self._accept)

    def _accept(self) -> None:
        try:
            conn, _ = self._sock.accept()
        except BlockingIOError:
            return
        with conn:
            conn.settimeout(0.5)
            try:
                data = conn.recv(64).decode("utf-8", errors="replace").strip()
            except OSError:
                return
        if data:
            self._on_command(data.split()[0].lower())

    def close(self) -> None:
        self._notifier.setEnabled(False)
        try:
            self._sock.close()
        except OSError:
            pass
        try:
            SOCK_PATH.unlink()
        except OSError:
            pass
