from __future__ import annotations

from typing import Any, Callable

from PyQt5.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot


# OCR, 번역은 오래 걸려서 백그라운드 스레드에서 돌림
# (예전엔 processEvents() 계속 불러서 창 멈추는거 막았었음)
class WorkerSignals(QObject):
    finished = pyqtSignal(object)
    failed = pyqtSignal(str)


class Worker(QRunnable):
    def __init__(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        super().__init__()
        self.fn, self.args, self.kwargs = fn, args, kwargs
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self) -> None:
        try:
            result = self.fn(*self.args, **self.kwargs)
        except Exception as exc:  # noqa: BLE001 - 에러나면 상태바에 띄움
            self.signals.failed.emit(str(exc))
        else:
            self.signals.finished.emit(result)
