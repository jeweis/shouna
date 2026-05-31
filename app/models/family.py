from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from app.core.database import Base

class Family(Base):
    __tablename__ = "families"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系属性
    members = relationship("FamilyMember", back_populates="family", cascade="all, delete-orphan")
    locations = relationship("Location", back_populates="family", cascade="all, delete-orphan")
    items = relationship("Item", back_populates="family", cascade="all, delete-orphan")
    item_photos = relationship("ItemPhoto", back_populates="family", cascade="all, delete-orphan")
    location_photos = relationship("LocationPhoto", back_populates="family", cascade="all, delete-orphan")


class FamilyMember(Base):
    __tablename__ = "family_members"

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String, default="member")  # admin, member
    joined_at = Column(DateTime, default=datetime.utcnow)

    # 关系属性
    family = relationship("Family", back_populates="members")
    user = relationship("User", back_populates="family_memberships")
