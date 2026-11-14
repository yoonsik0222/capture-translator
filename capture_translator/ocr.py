from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

import pytesseract
from PIL import Image, ImageOps

# 콤보박스에 보이는 이름 : tesseract 언어 코드
OCR_LANGUAGES: dict[str, str] = {
    "자동 (한/영/일)": "kor+eng+jpn",
    "영어": "eng",
    "한국어": "kor",
    "일본어": "jpn",
    "일본어 (세로쓰기)": "jpn_vert",
}

_WINDOWS_DEFAULT_PATHS = [
    Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
    Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
    Path(os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe")),
]


class OcrError(RuntimeError):
    pass


# 01. tesseract 위치 찾기 (설정값 > PATH > 기본 설치 경로 순)
def find_tesseract(explicit: str | None = None) -> str | None:
    if explicit and Path(explicit).exists():
        return explicit
    on_path = shutil.which("tesseract")
    if on_path:
        return on_path
    for candidate in _WINDOWS_DEFAULT_PATHS:
        if candidate.exists():
            return str(candidate)
    return None


def configure(tesseract_cmd: str | None = None) -> str:
    path = find_tesseract(tesseract_cmd)
    if path is None:
        raise OcrError(
            "Tesseract를 찾을 수 없습니다. 설치 후 PATH에 추가하거나 "
            ".env 의 TESSERACT_CMD 에 경로를 지정해 주세요."
        )
    pytesseract.pytesseract.tesseract_cmd = path
    return path


def available_languages() -> set[str]:
    try:
        return set(pytesseract.get_languages(config=""))
    except pytesseract.TesseractError:
        return set()


# 02. 인식률 올리려고 흑백으로 바꾸고, 작은 이미지는 키우는 구문
def preprocess(image: Image.Image, min_height: int = 600) -> Image.Image:
    gray = ImageOps.grayscale(image)
    if gray.height < min_height:
        scale = min(3.0, min_height / max(gray.height, 1))  # 최대 3배까지만
        gray = gray.resize(
            (int(gray.width * scale), int(gray.height * scale)), Image.Resampling.LANCZOS
        )
    return gray


# 03. 이미지에서 텍스트 뽑기
def extract_text(image: Image.Image, lang: str = "kor+eng+jpn") -> str:
    try:
        raw = pytesseract.image_to_string(preprocess(image), lang=lang)
    except (pytesseract.TesseractError, pytesseract.TesseractNotFoundError) as exc:
        raise OcrError(f"OCR 실패: {exc}") from exc
    return clean_text(raw)


# 한자, 히라가나, 가타카나, 전각기호 (한글은 띄어쓰기 있어서 뺌)
_CJK = r"\u3000-\u303f\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uff00-\uffef"
_CJK_SPACE = re.compile(rf"(?<=[{_CJK}]) +(?=[{_CJK}])")
_CJK_CHAR = re.compile(rf"[{_CJK}]")


# 04. OCR 결과 정리 구문 (번역 잘 되게)
def clean_text(text: str) -> str:
    paragraphs: list[str] = []
    current = ""
    for line in text.replace("\f", "\n").splitlines():
        line = _CJK_SPACE.sub("", line.strip())  # 일본어 글자 사이 공백 제거
        if not line:  # 빈 줄 = 문단 끝
            if current:
                paragraphs.append(current)
                current = ""
            continue
        if not current:
            current = line
        elif re.search(r"[A-Za-z]-$", current) and line[0].islower():
            current = current[:-1] + line  # exam- / ple -> example
        elif _CJK_CHAR.match(current[-1]) and _CJK_CHAR.match(line[0]):
            current += line  # 일본어/중국어는 띄어쓰기 없이 붙임
        else:
            current += " " + line
    if current:
        paragraphs.append(current)
    return "\n\n".join(paragraphs)
