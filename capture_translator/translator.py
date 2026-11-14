from __future__ import annotations

from dataclasses import dataclass

import requests

# 콤보박스에 보이는 이름 : 언어 코드
TARGET_LANGUAGES: dict[str, str] = {
    "한국어": "ko",
    "영어": "en",
    "일본어": "ja",
    "중국어(간체)": "zh-CN",
    "중국어(번체)": "zh-TW",
    "스페인어": "es",
    "프랑스어": "fr",
    "독일어": "de",
}

LANGUAGE_NAMES: dict[str, str] = {code: name for name, code in TARGET_LANGUAGES.items()}


class TranslationError(RuntimeError):
    pass


@dataclass(frozen=True)
class TranslationResult:
    text: str
    source_lang: str | None  # 감지된 언어


# Google 번역 (무료 Papago API 지원 종료로 Google 번역 사용)
class GoogleWebTranslator:
    name = "Google"
    URL = "https://translate.googleapis.com/translate_a/single"

    def __init__(self, session: requests.Session | None = None, timeout: float = 10.0):
        self.session = session or requests.Session()
        self.timeout = timeout

    def translate(self, text: str, target: str, source: str = "auto") -> TranslationResult:
        if not text.strip():
            return TranslationResult("", None)
        try:
            # 텍스트 길면 GET 주소가 너무 길어져서 POST로 보냄
            resp = self.session.post(
                self.URL,
                params={"client": "gtx", "sl": source, "tl": target, "dt": "t"},
                data={"q": text},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        except (requests.RequestException, ValueError) as exc:
            raise TranslationError(f"Google 번역 요청 실패: {exc}") from exc
        return self.parse_response(data)

    @staticmethod
    def parse_response(data: list) -> TranslationResult:
        # data[0] = 문장별 번역 결과, data[2] = 감지된 언어
        try:
            translated = "".join(seg[0] for seg in data[0] if seg and seg[0])
            detected = data[2] if len(data) > 2 and isinstance(data[2], str) else None
        except (IndexError, TypeError) as exc:
            raise TranslationError("예상하지 못한 응답 형식입니다.") from exc
        return TranslationResult(translated, detected)
