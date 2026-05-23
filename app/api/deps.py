from typing import Generator, Optional
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
import jwt
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import ALGORITHM
from app.core.database import SessionLocal
from app.repositories.user import user_repo
from app.repositories.family import family_repo
from app.models.user import User
from app.schemas.token import TokenPayload

# 声明 OAuth2 密码流，指定 Token 获取的 API 端点
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[ALGORITHM]
        )
        token_data = TokenPayload(**payload)
        user_id = int(token_data.sub)
    except (jwt.PyJWTError, ValidationError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效凭证，请重新登录",
        )
    user = user_repo.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户账号已被禁用"
        )
    return user

def get_current_family(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    x_family_id: Optional[int] = Header(None, alias="X-Family-Id")
) -> int:
    """
    依赖注入校验器：获取用户当前操作的家庭 ID，防止跨家庭越权访问。
    """
    # 1. 查找用户的所有家庭
    user_families = family_repo.get_user_families(db, user_id=current_user.id)
    if not user_families:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户不属于任何家庭，请先创建或加入一个家庭"
        )

    # 2. 如果请求头指定了家庭 ID，进行越权校验
    if x_family_id is not None:
        member = family_repo.get_membership(db, family_id=x_family_id, user_id=current_user.id)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="越权访问：您不属于指定的家庭工作空间"
            )
        return x_family_id

    # 3. 如果请求头未指定，默认返回用户绑定的第一个家庭
    return user_families[0].id
