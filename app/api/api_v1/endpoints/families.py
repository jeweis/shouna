from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.api import deps
from app.models.user import User
from app.repositories.family import family_repo
from app.schemas.family import FamilyCreate, FamilyMemberResponse, FamilyResponse
from app.services.family_service import family_service

router = APIRouter()


class AddFamilyMemberRequest(BaseModel):
    email: EmailStr


@router.post("/", response_model=FamilyResponse, status_code=status.HTTP_201_CREATED)
def create_family(
    *,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    family_in: FamilyCreate,
) -> Any:
    """
    当前用户创建一个新的家庭工作空间。
    """
    return family_service.create_family_for_user(
        db, name=family_in.name, user_id=current_user.id
    )


@router.get("/current/members", response_model=List[FamilyMemberResponse])
def get_current_family_members(
    *,
    db: Session = Depends(deps.get_db),
    family_id: int = Depends(deps.get_current_family),
) -> Any:
    """
    查询当前家庭工作空间成员列表。
    """
    return family_service.get_family_members(db, family_id=family_id)


@router.post(
    "/current/members",
    response_model=FamilyMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_current_family_member(
    *,
    db: Session = Depends(deps.get_db),
    family_id: int = Depends(deps.get_current_family),
    current_user: User = Depends(deps.get_current_user),
    req: AddFamilyMemberRequest,
) -> Any:
    """
    当前家庭管理员按邮箱添加已有用户加入家庭。
    """
    membership = family_repo.get_membership(
        db, family_id=family_id, user_id=current_user.id
    )
    if not membership or membership.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有家庭管理员可以添加成员",
        )

    member = family_service.join_family(
        db, family_id=family_id, user_email=req.email, role="member"
    )
    if not member:
        raise HTTPException(status_code=404, detail="用户不存在")
    return member
