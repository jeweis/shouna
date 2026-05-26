from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.api import deps
from app.schemas.item_photo import ItemPhotoResponse
from app.services.item_photo_service import item_photo_service

router = APIRouter()


@router.get("/{photo_id}/content")
def get_item_photo_content(
    *,
    db: Session = Depends(deps.get_db),
    family_id: int = Depends(deps.get_current_family),
    photo_id: int,
) -> Any:
    """
    读取当前家庭可见的物品图片二进制内容。
    """
    try:
        photo, content = item_photo_service.get_photo_content(
            db, photo_id=photo_id, family_id=family_id
        )
        return Response(content=content, media_type=photo.mime_type)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{photo_id}", response_model=ItemPhotoResponse)
def delete_item_photo(
    *,
    db: Session = Depends(deps.get_db),
    family_id: int = Depends(deps.get_current_family),
    photo_id: int,
) -> Any:
    """
    删除当前家庭可见的单张物品图片。
    """
    try:
        return item_photo_service.delete_photo(db, photo_id=photo_id, family_id=family_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
