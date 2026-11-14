# GUI 테스트 (화면 없이 offscreen으로 창 띄워서 OCR > 번역까지 되는지 확인)

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt5.QtCore import QThreadPool
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QApplication

from capture_translator import ocr
from capture_translator.app import MainWindow
from capture_translator.config import Settings
from capture_translator.translator import TranslationResult


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


class FakeTranslator:
    name = "Fake"

    def translate(self, text, target, source="auto"):
        return TranslationResult(f"[{target}] {text}", "en")


def _wait(app, window):
    # OCR 끝나면 번역이 이어서 시작돼서, 작업 다 끝날 때까지 반복
    for _ in range(20):
        QThreadPool.globalInstance().waitForDone(30000)
        app.processEvents()
        if window._busy == 0:
            return


@pytest.mark.skipif(ocr.find_tesseract() is None, reason="Tesseract 미설치")
def test_window_ocr_and_translate(qapp, tmp_path):
    from tests.test_ocr import _render

    path = tmp_path / "sample.png"
    _render("Hello world").save(path)

    window = MainWindow(Settings(capture_dir=tmp_path))
    window.translator = FakeTranslator()
    window.ocrLangCombo.setCurrentText("영어")
    window.targetLangCombo.setCurrentText("한국어")

    window.load_pixmap(QPixmap(str(path)))
    _wait(qapp, window)

    assert "Hello world" in window.sourceEdit.toPlainText()
    assert window.resultEdit.toPlainText().startswith("[ko] Hello world")
    assert "영어" in window.detectedLabel.text()
