from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship, backref
from app.core.database import Base

class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    # parent_id 允许空间无限嵌套。ondelete="CASCADE" 确保级联删除
    parent_id = Column(Integer, ForeignKey("locations.id", ondelete="CASCADE"), nullable=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系属性：自关联树形结构
    # remote_side=[id] 表明这是一个自关联，由 parent 指向自身的 id。
    sub_locations = relationship(
        "Location",
        backref=backref("parent", remote_side=[id]),
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    family = relationship("Family", back_populates="locations")
    items = relationship(
        "Item",
        back_populates="location",
        cascade="all, delete-orphan",
        passive_deletes=True,
        foreign_keys="Item.location_id"
    )
