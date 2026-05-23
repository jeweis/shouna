from typing import List, Optional
from sqlalchemy.orm import Session
from app.repositories.base import BaseRepository
from app.models.family import Family, FamilyMember
from app.models.user import User
from app.schemas.family import FamilyCreate

class FamilyRepository(BaseRepository[Family, FamilyCreate, FamilyCreate]):
    def add_member(self, db: Session, *, family_id: int, user_id: int, role: str = "member") -> FamilyMember:
        member = FamilyMember(family_id=family_id, user_id=user_id, role=role)
        db.add(member)
        db.commit()
        db.refresh(member)
        return member

    def get_membership(self, db: Session, *, family_id: int, user_id: int) -> Optional[FamilyMember]:
        return db.query(FamilyMember).filter(
            FamilyMember.family_id == family_id,
            FamilyMember.user_id == user_id
        ).first()

    def get_members(self, db: Session, *, family_id: int) -> List[FamilyMember]:
        return db.query(FamilyMember).filter(FamilyMember.family_id == family_id).all()

    def get_user_families(self, db: Session, *, user_id: int) -> List[Family]:
        memberships = db.query(FamilyMember).filter(FamilyMember.user_id == user_id).all()
        return [m.family for m in memberships]

family_repo = FamilyRepository(Family)
