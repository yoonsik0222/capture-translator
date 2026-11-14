import pytest
from PIL import Image, ImageDraw, ImageFont

from capture_translator import ocr


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Hello\nworld", "Hello world"),
        ("first para\n\n\nsecond\npara", "first para\n\nsecond para"),
        ("an exam-\nple text", "an example text"),
        ("well-\nKnown", "well- Known"),  # 대문자면 하이픈 그대로
        ("こ ん に ち は\n世 界", "こんにちは世界"),
        ("안녕 하세요\n반갑습니다", "안녕 하세요 반갑습니다"),  # 한글 띄어쓰기는 그대로
        ("  \n text \f", "text"),
        ("", ""),
    ],
)
def test_clean_text(raw, expected):
    assert ocr.clean_text(raw) == expected


def test_preprocess_grayscale_and_upscale():
    img = Image.new("RGB", (200, 100), "white")
    out = ocr.preprocess(img, min_height=300)
    assert out.mode == "L"
    assert out.size == (600, 300)


def test_preprocess_keeps_large_images():
    img = Image.new("RGB", (1000, 800), "white")
    assert ocr.preprocess(img, min_height=600).size == (1000, 800)


def _render(text: str) -> Image.Image:
    img = Image.new("RGB", (900, 120), "white")
    try:
        font = ImageFont.truetype("arial.ttf", 48)
    except OSError:
        font = ImageFont.load_default(size=48)
    ImageDraw.Draw(img).text((20, 30), text, fill="black", font=font)
    return img


@pytest.mark.skipif(ocr.find_tesseract() is None, reason="Tesseract 미설치")
def test_extract_text_end_to_end():
    ocr.configure()
    text = ocr.extract_text(_render("Capture Translator 2026"), lang="eng")
    assert "Capture Translator" in text
