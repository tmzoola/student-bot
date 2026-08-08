from models.base import Base
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column


class LandingContent(Base):
    __tablename__ = "landing_content"

    badge_text: Mapped[str] = mapped_column(String(200))
    hero_title_before: Mapped[str] = mapped_column(String(200))
    hero_title_highlight: Mapped[str] = mapped_column(String(100))
    hero_title_after: Mapped[str] = mapped_column(String(200))
    hero_subtitle: Mapped[str] = mapped_column(Text)
    primary_btn_label: Mapped[str] = mapped_column(String(100))
    secondary_btn_label: Mapped[str] = mapped_column(String(100))
    daily_title: Mapped[str] = mapped_column(String(200))

    def __str__(self) -> str:
        return "Bosh sahifa matni"
