from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base

class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    quantity = Column(Integer, default=1, nullable=False)
    # JSON 类型在 SQLite 中底层映射为 Text (支持 JSON 运算符)，在 PostgreSQL 中映射为 JSON/JSONB
    tags = Column(JSON, default=list, nullable=False)
    photo_url = Column(String, nullable=True)

    # 常用常驻空间 (用于一键归位功能)
    home_location_id = Column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)

    # 当前实际位置 (外键关联空间，当空间级联删除时，对应物品级联删除)
    location_id = Column(Integer, ForeignKey("locations.id", ondelete="CASCADE"), nullable=False, index=True)

    # 数据所属的家庭域 (安全防护，外键关联)
    family_id = Column(Integer, ForeignKey("families.id", ondelete="CASCADE"), nullable=False, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系属性
    location = relationship("Location", back_populates="items", foreign_keys=[location_id])
    home_location = relationship("Location", foreign_keys=[home_location_id])
    family = relationship("Family", back_populates="items")
    photos = relationship("ItemPhoto", back_populates="item", cascade="all, delete-orphan")
