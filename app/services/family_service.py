from typing import List, Optional
from sqlalchemy.orm import Session
from app.repositories.family import family_repo
from app.repositories.user import user_repo
from app.models.family import Family, FamilyMember
from app.models.user import User
from app.schemas.family import FamilyCreate

class FamilyService:
    def create_family_for_user(self, db: Session, *, name: str, user_id: int) -> Family:
        """
        创建新的家庭工作空间，并将创建者设为管理员。
        """
        family = family_repo.create(db, obj_in=FamilyCreate(name=name))
        family_repo.add_member(db, family_id=family.id, user_id=user_id, role="admin")
        db.refresh(family)
        return family

    def join_family(self, db: Session, *, family_id: int, user_email: str, role: str = "member") -> Optional[FamilyMember]:
        """
        邀请/添加一个用户加入当前家庭工作空间。
        """
        # 1. 查找用户是否存在
        user = user_repo.get_by_email(db, email=user_email)
        if not user:
            return None

        # 2. 检查是否已经是该家庭的成员
        existing_membership = family_repo.get_membership(db, family_id=family_id, user_id=user.id)
        if existing_membership:
            return existing_membership

        # 3. 添加加入
        return family_repo.add_member(db, family_id=family_id, user_id=user.id, role=role)

    def get_family_members(self, db: Session, *, family_id: int) -> List[FamilyMember]:
        """
        查询家庭中的所有成员。
        """
        return family_repo.get_members(db, family_id=family_id)

    def get_user_families(self, db: Session, *, user_id: int) -> List[Family]:
        """
        获取一个用户所属的所有家庭。
        """
        return family_repo.get_user_families(db, user_id=user_id)

family_service = FamilyService()
