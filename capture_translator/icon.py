from __future__ import annotations

from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QColor, QFont, QIcon, QPainter, QPixmap


# 앱 아이콘 (이미지 파일 없이 직접 그림)
def app_icon(size: int = 256) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    p = QPainter(pixmap)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)

    # 뒤쪽 회색 박스, 앞쪽 파란 박스
    p.setBrush(QColor("#E8EAF0"))
    p.drawRoundedRect(QRectF(size * 0.34, size * 0.30, size * 0.62, size * 0.62), size * 0.1, size * 0.1)
    p.setBrush(QColor("#3B6FE0"))
    p.drawRoundedRect(QRectF(size * 0.04, size * 0.06, size * 0.60, size * 0.60), size * 0.1, size * 0.1)

    font = QFont("Malgun Gothic")
    font.setBold(True)
    font.setPixelSize(int(size * 0.38))
    p.setFont(font)
    p.setPen(Qt.white)
    p.drawText(QRectF(size * 0.04, size * 0.06, size * 0.60, size * 0.60), Qt.AlignCenter, "가")
    p.setPen(QColor("#2B3A55"))
    p.drawText(QRectF(size * 0.48, size * 0.40, size * 0.48, size * 0.52), Qt.AlignCenter, "A")
    p.end()
    return QIcon(pixmap)
