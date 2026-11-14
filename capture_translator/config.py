from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# .env 파일 불러오기
try:
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:  # dotenv 없으면 그냥 환경변수만 사용
    pass


@dataclass(frozen=True)
class Settings:
    tesseract_cmd: str | None = None
    capture_dir: Path = PROJECT_ROOT / "captures"

    @classmethod
    def from_env(cls) -> "Settings":
        capture_dir = os.getenv("CAPTURE_DIR")
        return cls(
            tesseract_cmd=os.getenv("TESSERACT_CMD") or None,
            capture_dir=Path(capture_dir) if capture_dir else cls.capture_dir,
        )
