from __future__ import annotations

import io
import sys
from datetime import datetime
from pathlib import Path

from PIL import Image
from PyQt5 import uic  # Ui module
from PyQt5.QtCore import QBuffer, QIODevice, Qt, QThreadPool, QTimer
from PyQt5.QtGui import QKeySequence, QPixmap
from PyQt5.QtWidgets import QApplication, QFileDialog, QMainWindow, QShortcut

from capture_translator import __version__, ocr
from capture_translator.config import Settings
from capture_translator.icon import app_icon
from capture_translator.overlay import SnipOverlay
from capture_translator.translator import (
    LANGUAGE_NAMES,
    TARGET_LANGUAGES,
    GoogleWebTranslator,
    TranslationResult,
)
from capture_translator.workers import Worker

# 실행 위치 상관없이 ui 파일 찾게 절대경로로
UI_FILE = Path(__file__).resolve().parent / "ui" / "main_window.ui"


# QPixmap -> PIL 이미지 변환
def pixmap_to_pil(pixmap: QPixmap) -> Image.Image:
    buffer = QBuffer()
    buffer.open(QIODevice.WriteOnly)
    pixmap.save(buffer, "PNG")
    return Image.open(io.BytesIO(bytes(buffer.data()))).convert("RGB")


class MainWindow(QMainWindow):
    def __init__(self, settings: Settings | None = None) -> None:
        super().__init__()
        uic.loadUi(UI_FILE, self)
        self.settings = settings or Settings.from_env()
        self.translator = GoogleWebTranslator()
        self.pool = QThreadPool.globalInstance()
        self.current_image: Image.Image | None = None
        self._pixmap: QPixmap | None = None
        self._busy = 0  # 돌아가고 있는 작업 수

        self.setWindowTitle(f"캡처 번역기 v{__version__}")  # GUI screen name
        self.setWindowIcon(app_icon())
        self.splitter.setSizes([260, 640])

        self.ocrLangCombo.addItems(ocr.OCR_LANGUAGES.keys())
        self.targetLangCombo.addItems(TARGET_LANGUAGES.keys())

        # Button click signal
        self.captureButton.clicked.connect(self.start_capture)
        self.openButton.clicked.connect(self.open_image)
        self.rerunOcrButton.clicked.connect(self.run_ocr)
        self.translateButton.clicked.connect(self.translate)
        self.copyResultButton.clicked.connect(self.copy_result)
        self.targetLangCombo.currentIndexChanged.connect(self._retranslate_if_ready)
        # 단축키
        QShortcut(QKeySequence("Ctrl+Shift+S"), self, activated=self.start_capture)
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self.translate)

        self._check_tesseract()

    # 00. 시작할 때 tesseract 설치 확인
    def _check_tesseract(self) -> None:
        try:
            ocr.configure(self.settings.tesseract_cmd)
        except ocr.OcrError as exc:
            self._set_ocr_enabled(False)
            self.status(str(exc), error=True)
            return
        installed = ocr.available_languages()
        missing = {"kor", "eng", "jpn"} - installed
        msg = f"준비 완료 · 번역 엔진: {self.translator.name}"
        if missing:
            msg += f" · 설치되지 않은 OCR 언어: {', '.join(sorted(missing))}"
        self.status(msg)

    def _set_ocr_enabled(self, enabled: bool) -> None:
        for w in (self.captureButton, self.openButton, self.rerunOcrButton):
            w.setEnabled(enabled)

    # 01. 이미지 캡쳐 구문
    def start_capture(self) -> None:
        if not self.captureButton.isEnabled():
            return
        self.hide()
        # 창 다 사라지고 나서 찍어야 캡쳐에 이 창이 안 찍힘
        QTimer.singleShot(250, self._show_overlay)

    def _show_overlay(self) -> None:
        self._overlay = SnipOverlay()
        self._overlay.captured.connect(self._on_captured)
        self._overlay.cancelled.connect(self._restore_window)
        self._overlay.show()
        self._overlay.activateWindow()

    def _restore_window(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def _on_captured(self, pixmap: QPixmap) -> None:
        self._restore_window()
        if self.copyImageCheck.isChecked():
            QApplication.clipboard().setPixmap(pixmap)  # 캡쳐 이미지 클립보드로 복사
        if self.saveCheck.isChecked():
            self._save_capture(pixmap)
        self.load_pixmap(pixmap)

    # 캡쳐 이미지 저장 (파일 이름은 날짜_시간으로, 덮어쓰기 방지)
    def _save_capture(self, pixmap: QPixmap) -> None:
        folder = self.settings.capture_dir
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"capture_{datetime.now():%Y%m%d_%H%M%S}.png"
        pixmap.save(str(path), "PNG")
        self.status(f"저장됨: {path}")

    def open_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "이미지 열기", "", "이미지 (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if path:
            pixmap = QPixmap(path)
            if pixmap.isNull():
                self.status("이미지를 열 수 없습니다.", error=True)
                return
            self.load_pixmap(pixmap)

    def load_pixmap(self, pixmap: QPixmap) -> None:
        self._pixmap = pixmap
        self.current_image = pixmap_to_pil(pixmap)
        self._update_preview()
        self.run_ocr()

    # 왼쪽 미리보기 (창 크기 맞춰서)
    def _update_preview(self) -> None:
        if self._pixmap is not None:
            self.previewLabel.setPixmap(
                self._pixmap.scaled(
                    self.previewLabel.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            )

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_preview()

    # 02. 캡쳐한 이미지에서 tesseract로 글자 읽어오기
    def run_ocr(self) -> None:
        if self.current_image is None:
            self.status("먼저 화면을 캡처하거나 이미지를 열어 주세요.", error=True)
            return
        lang = ocr.OCR_LANGUAGES[self.ocrLangCombo.currentText()]
        self.sourceEdit.clear()
        self.resultEdit.clear()
        self.detectedLabel.clear()
        self._run(ocr.extract_text, self._on_ocr_done, "글자를 인식하는 중...",
                  self.current_image, lang)

    def _on_ocr_done(self, text: str) -> None:
        self.sourceEdit.setPlainText(text)
        if not text:
            self.status("인식된 글자가 없습니다. 영역을 더 크게 잡거나 OCR 언어를 바꿔 보세요.",
                        error=True)
            return
        self.status(f"{len(text)}자 인식 완료")
        self.translate()  # 인식 끝나면 바로 번역

    # 03. 번역 구문
    def translate(self) -> None:
        text = self.sourceEdit.toPlainText().strip()  # 원문 직접 고친 경우도 반영
        if not text:
            self.status("번역할 텍스트가 없습니다.", error=True)
            return
        target = TARGET_LANGUAGES[self.targetLangCombo.currentText()]
        self._run(self.translator.translate, self._on_translated, "번역하는 중...",
                  text, target)

    # 번역할 언어 바꾸면 다시 번역
    def _retranslate_if_ready(self) -> None:
        if self.sourceEdit.toPlainText().strip() and self._busy == 0:
            self.translate()

    def _on_translated(self, result: TranslationResult) -> None:
        self.resultEdit.setPlainText(result.text)
        if result.source_lang:
            name = LANGUAGE_NAMES.get(result.source_lang, result.source_lang)
            self.detectedLabel.setText(f"(감지된 언어: {name})")
        self.status(f"번역 완료 · {self.translator.name}")

    def copy_result(self) -> None:
        text = self.resultEdit.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            self.status("번역 결과를 클립보드에 복사했습니다.")

    # 백그라운드로 작업 돌리는 공통 함수
    def _run(self, fn, on_done, message: str, *args) -> None:
        worker = Worker(fn, *args)
        worker.signals.finished.connect(on_done)
        worker.signals.failed.connect(lambda err: self.status(err, error=True))
        worker.signals.finished.connect(self._task_done)
        worker.signals.failed.connect(self._task_done)
        self._busy += 1
        self.status(message)
        self.pool.start(worker)

    def _task_done(self, *_):
        self._busy = max(0, self._busy - 1)

    # 아래 상태바 메시지 (에러면 빨간색)
    def status(self, message: str, error: bool = False) -> None:
        self.statusbar.setStyleSheet("color: #c0392b;" if error else "")
        self.statusbar.showMessage(message)


def main() -> None:
    # 고해상도 모니터 대응
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName("Capture Translator")
    app.setStyleSheet("QPushButton { padding: 5px 14px; }")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
