from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class LocationPhoto(Base):
    __tablename__ = "location_photos"

    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer, ForeignKey("locations.id", ondelete="CASCADE"), nullable=False, index=True)
    family_id = Column(Integer, ForeignKey("families.id", ondelete="CASCADE"), nullable=False, index=True)
    storage_provider = Column(String, default="local", nullable=False)
    storage_key = Column(String, nullable=False, unique=True, index=True)
    mime_type = Column(String, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 空间照片用于找物定位，权限始终跟随家庭和空间。
    location = relationship("Location", back_populates="locator_photos")
    family = relationship("Family", back_populates="location_photos")
