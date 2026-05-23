from typing import Optional, Tuple
from sqlalchemy.orm import Session
from app.repositories.user import user_repo
from app.repositories.family import family_repo
from app.models.user import User
from app.models.family import Family
from app.schemas.user import UserCreate
from app.core.security import verify_password

class UserService:
    def register_user(self, db: Session, *, user_in: UserCreate, family_name: Optional[str] = None) -> Tuple[User, Family]:
        """
        注册新用户并自动绑定/生成一个新的家庭工作空间。
        """
        # 1. 创建用户
        user = user_repo.create(db, obj_in=user_in)

        # 2. 如果未指定家庭名称，默认使用 "xxx 的家庭"
        if not family_name:
            family_name = f"{user.full_name or '新用户'} 的家庭"

        # 3. 创建家庭
        from app.schemas.family import FamilyCreate
        family_in = FamilyCreate(name=family_name)
        family = family_repo.create(db, obj_in=family_in)

        # 4. 绑定用户为该家庭的管理员 (admin)
        family_repo.add_member(db, family_id=family.id, user_id=user.id, role="admin")

        return user, family

    def authenticate(self, db: Session, *, email: str, password: str) -> Optional[User]:
        """
        用户登录身份认证。
        """
        user = user_repo.get_by_email(db, email=email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

user_service = UserService()
