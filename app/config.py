import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    telegram_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    image_model: str = os.getenv("IMAGE_MODEL", "gpt-image-2.5-sunburst")
    image_quality: str = os.getenv("IMAGE_QUALITY", "high")
    work_dir: str = os.getenv("WORK_DIR", "/data/work")
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "20"))
    live_photo_seconds: float = float(os.getenv("LIVE_PHOTO_SECONDS", "3.0"))
    admin_ids: tuple = tuple(
        int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()
    )

settings = Settings()
