from datetime import timedelta
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from app.api import deps
from app.core.security import create_access_token
from app.repositories.user import user_repo
from app.services.user_service import user_service
from app.schemas.user import UserResponse, UserCreate
from app.schemas.family import FamilyResponse
from app.schemas.token import Token

router = APIRouter()

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    family_name: Optional[str] = None

class RegisterResponse(BaseModel):
    user: UserResponse
    family: FamilyResponse
    access_token: str
    token_type: str

@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(
    *,
    db: Session = Depends(deps.get_db),
    req: RegisterRequest
) -> Any:
    """
    新用户注册，并自动生成默认家庭。
    """
    user = user_repo.get_by_email(db, email=req.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该邮箱已被注册"
        )

    user_in = UserCreate(
        email=req.email,
        password=req.password,
        full_name=req.full_name
    )
    user, family = user_service.register_user(db, user_in=user_in, family_name=req.family_name)
    return {
        "user": user,
        "family": family,
        "access_token": create_access_token(user.id),
        "token_type": "bearer",
    }


@router.post("/login", response_model=Token)
def login(
    db: Session = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 密码登录 (Swagger 兼容形式)
    """
    user = user_service.authenticate(
        db, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱或密码错误"
        )
    return {
        "access_token": create_access_token(user.id),
        "token_type": "bearer",
    }


class JsonLoginRequest(BaseModel):
    email: EmailStr
    password: str

@router.post("/login/json", response_model=Token)
def login_json(
    db: Session = Depends(deps.get_db),
    req: JsonLoginRequest = None
) -> Any:
    """
    标准的 JSON 登录端点，便于 Flutter 移动端直接调用
    """
    if not req:
        raise HTTPException(status_code=400, detail="请求体不能为空")
    user = user_service.authenticate(
        db, email=req.email, password=req.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱或密码错误"
        )
    return {
        "access_token": create_access_token(user.id),
        "token_type": "bearer",
    }


@router.get("/me/families", response_model=List[FamilyResponse])
def get_my_families(
    db: Session = Depends(deps.get_db),
    current_user: UserResponse = Depends(deps.get_current_user)
) -> Any:
    """
    获取当前登录用户所属的所有家庭工作空间列表。
    """
    from app.services.family_service import family_service
    # 为了防止 UserResponse pydantic 数据绑定丢失，直接使用 current_user.id。
    # 集中在 app 作用域解析
    return family_service.get_user_families(db, user_id=current_user.id)
