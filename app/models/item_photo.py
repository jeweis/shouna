from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class ItemPhoto(Base):
    __tablename__ = "item_photos"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True)
    family_id = Column(Integer, ForeignKey("families.id", ondelete="CASCADE"), nullable=False, index=True)
    storage_provider = Column(String, default="local", nullable=False)
    storage_key = Column(String, nullable=False, unique=True, index=True)
    mime_type = Column(String, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系属性用于家庭隔离校验与物品级联删除。
    item = relationship("Item", back_populates="photos")
    family = relationship("Family", back_populates="item_photos")
