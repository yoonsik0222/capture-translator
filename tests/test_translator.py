from unittest.mock import MagicMock

import pytest
import requests

from capture_translator.translator import GoogleWebTranslator, TranslationError

SAMPLE = [
    [["안녕하세요, ", "Hello, ", None], ["세계.", "world.", None]],
    None,
    "en",
]


def test_parse_google_response():
    result = GoogleWebTranslator.parse_response(SAMPLE)
    assert result.text == "안녕하세요, 세계."
    assert result.source_lang == "en"


def test_parse_google_response_invalid():
    with pytest.raises(TranslationError):
        GoogleWebTranslator.parse_response([])


def test_google_translate_uses_session():
    session = MagicMock()
    session.post.return_value.json.return_value = SAMPLE
    result = GoogleWebTranslator(session=session).translate("Hello, world.", "ko")
    assert result.text == "안녕하세요, 세계."
    kwargs = session.post.call_args.kwargs
    assert kwargs["params"]["tl"] == "ko"
    assert kwargs["data"] == {"q": "Hello, world."}


def test_google_translate_network_error():
    session = MagicMock()
    session.post.side_effect = requests.ConnectionError("offline")
    with pytest.raises(TranslationError):
        GoogleWebTranslator(session=session).translate("Hello", "ko")


def test_empty_text_skips_request():
    session = MagicMock()
    result = GoogleWebTranslator(session=session).translate("   ", "ko")
    assert result.text == ""
    session.post.assert_not_called()
