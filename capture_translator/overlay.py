from __future__ import annotations

from PyQt5.QtCore import QPoint, QRect, QSize, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QCursor, QGuiApplication, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import QWidget

MIN_SIZE = 5  # 이것보다 작으면 그냥 클릭 실수로 봄


# 화면 멈춰놓고 드래그로 캡쳐 영역 고르는 창
# (예전엔 shift 두 번 눌러서 왼쪽 위 > 오른쪽 아래 순으로만 됐음)
class SnipOverlay(QWidget):
    captured = pyqtSignal(QPixmap)
    cancelled = pyqtSignal()

    def __init__(self) -> None:
        super().__init__(
            None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setCursor(Qt.CrossCursor)
        self.setMouseTracking(True)

        # 마우스 있는 모니터 화면 캡쳐
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        self._screenshot = screen.grabWindow(0)
        self.setGeometry(screen.geometry())

        self._origin: QPoint | None = None
        self._current: QPoint | None = None

    # 드래그한 영역 (방향 상관없음)
    def selection(self) -> QRect:
        if self._origin is None or self._current is None:
            return QRect()
        a, b = self._origin, self._current
        # QRect(p1, p2)로 만들면 1px씩 커져서 크기로 만듦
        return QRect(
            QPoint(min(a.x(), b.x()), min(a.y(), b.y())),
            QSize(abs(a.x() - b.x()), abs(a.y() - b.y())),
        )

    def _crop(self, rect: QRect) -> QPixmap:
        # 배율 125%, 150% 같은 모니터는 실제 픽셀이 더 많아서 비율 맞춰줌
        ratio = self._screenshot.width() / max(self.width(), 1)
        physical = QRect(
            round(rect.x() * ratio),
            round(rect.y() * ratio),
            round(rect.width() * ratio),
            round(rect.height() * ratio),
        )
        cropped = self._screenshot.copy(physical)
        cropped.setDevicePixelRatio(1.0)
        return cropped

    # Mouse / Key event
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.RightButton:  # 우클릭 = 취소
            self._cancel()
        elif event.button() == Qt.LeftButton:
            self._origin = self._current = event.pos()
            self.update()

    def mouseMoveEvent(self, event) -> None:
        if self._origin is not None:
            self._current = event.pos()
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() != Qt.LeftButton or self._origin is None:
            return
        self._current = event.pos()
        rect = self.selection()
        if rect.width() < MIN_SIZE or rect.height() < MIN_SIZE:
            self._origin = self._current = None
            self.update()
            return
        pixmap = self._crop(rect)
        self.close()
        self.captured.emit(pixmap)  # 캡쳐 완료시 signal send

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Escape:
            self._cancel()

    def _cancel(self) -> None:
        self.close()
        self.cancelled.emit()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.drawPixmap(self.rect(), self._screenshot)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 110))  # 화면 어둡게

        rect = self.selection()
        if rect.isValid():
            # 선택한 부분만 원래 밝기로
            ratio = self._screenshot.width() / max(self.width(), 1)
            source = QRect(
                round(rect.x() * ratio), round(rect.y() * ratio),
                round(rect.width() * ratio), round(rect.height() * ratio),
            )
            painter.drawPixmap(rect, self._screenshot, source)
            painter.setPen(QPen(QColor(66, 133, 244), 2))
            painter.drawRect(rect.adjusted(0, 0, -1, -1))
            painter.setPen(Qt.white)
            painter.drawText(
                rect.left(), max(rect.top() - 6, 14),
                f"{source.width()} × {source.height()}",
            )
        else:
            painter.setPen(Qt.white)
            painter.drawText(
                self.rect().adjusted(0, 40, 0, 0), Qt.AlignHCenter | Qt.AlignTop,
                "드래그해서 번역할 영역을 선택하세요  ·  Esc / 우클릭: 취소",
            )
