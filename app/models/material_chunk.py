from typing import TYPE_CHECKING

from models.base import Base
from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from models.material import Material


class MaterialChunk(Base):
    __tablename__ = "material_chunks"

    material_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("materials.id", ondelete="CASCADE"),
        index=True,
    )
    order: Mapped[int] = mapped_column(Integer, default=0)
    text: Mapped[str] = mapped_column(Text)

    material: Mapped["Material"] = relationship("Material", back_populates="chunks")
