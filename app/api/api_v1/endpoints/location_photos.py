from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.api import deps
from app.schemas.location_photo import LocationPhotoResponse
from app.services.location_photo_service import location_photo_service

router = APIRouter()


@router.get("/{photo_id}/content")
def get_location_photo_content(
    *,
    db: Session = Depends(deps.get_db),
    family_id: int = Depends(deps.get_current_family),
    photo_id: int,
) -> Any:
    """
    读取当前家庭可见的空间定位照片二进制内容。
    """
    try:
        photo, content = location_photo_service.get_photo_content(
            db, photo_id=photo_id, family_id=family_id
        )
        return Response(content=content, media_type=photo.mime_type)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{photo_id}", response_model=LocationPhotoResponse)
def delete_location_photo(
    *,
    db: Session = Depends(deps.get_db),
    family_id: int = Depends(deps.get_current_family),
    photo_id: int,
) -> Any:
    """
    删除当前家庭可见的单张空间定位照片。
    """
    try:
        return location_photo_service.delete_photo(db, photo_id=photo_id, family_id=family_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
