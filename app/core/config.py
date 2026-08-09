from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Absolute media root (uploads) — independent of the process working dir.
# Resolves to <repo>/app/media; in Docker a volume is mounted here.
MEDIA_ROOT = Path(__file__).resolve().parent.parent / "media"

# Book upload constraints (shared by the admin tool page and the admin panel).
BOOKS_DIR_NAME = "books"
ALLOWED_BOOK_EXT = {
    ".pdf", ".doc", ".docx", ".ppt", ".pptx",
    ".xls", ".xlsx", ".epub", ".djvu", ".txt",
}
MAX_BOOK_SIZE = 100 * 1024 * 1024  # 100 MB

# Question image upload constraints (admin builder / contest builder).
QUESTION_IMAGES_DIR_NAME = "questions"
ALLOWED_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB

# Fixed book categories shown in the WebApp. Admin can still upload with
# custom categories for subjects not in this list — those simply won't appear
# as a default chip but are stored on the Book row unchanged.
BOOK_CATEGORIES = [
    "Tarbiyachilar",
    "Direktor o'rinbosari",
    "Psixologlar",
    "Logopedlar",
]


class Settings(BaseSettings):
    DEBUG: bool = False
    SECRET_KEY: str

    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str

    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str

    CORS_ALLOWED_ORIGINS: str = "http://localhost:8000"

    BOT_TOKEN: str
    # Deep-link URL'lari (`https://t.me/<BOT_USERNAME>?start=...`) uchun kerak.
    BOT_USERNAME: str = "student_bot"
    WEBAPP_URL: str = "http://localhost:8000"

    # Ro'yxatdan o'tgan talaba arizasi shu chat_id ga yuboriladi (admin guruhi
    # yoki shaxsiy admin). 0 bo'lsa notify o'tkazib yuboriladi (log warn).
    ADMIN_CHAT_ID: int = 0

    # Multi-worker umumiy kesh (subscription state va h.k.) — Redis URL.
    REDIS_URL: str = "redis://redis:6379/0"

    # ─── AI (Bosqich 5) ──────────────────────────────────────────────
    AI_PROVIDER: str = "claude"
    AI_MODEL: str = "claude-sonnet-4-6"
    ANTHROPIC_API_KEY: str = ""
    AI_DAILY_LIMIT_PER_USER: int = 20
    MAX_MATERIAL_SIZE: int = 20 * 1024 * 1024

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent / ".env"),
        extra="ignore",
    )


settings = Settings()
