"""Background OpenRouter calls so the UI stays responsive."""

from __future__ import annotations

from typing import Any, Callable

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from . import diag
from .capture import SnipCancelled


CANCELLED = "__cancelled__"


class FnWorker(QThread):
    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, fn: Callable[[], Any], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._fn = fn

    def run(self) -> None:
        try:
            result = self._fn()
        except SnipCancelled:
            self.failed.emit(CANCELLED)
            return
        except Exception as exc:
            diag.logger.exception("Background job failed")  # noqa: BLE001 — surface any API/IO failure to the UI
            self.failed.emit(str(exc))
            return
        self.succeeded.emit(result)
