from datetime import datetime
from typing import Any, Callable, List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status, UploadFile, File
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api import deps
from app.models.user import User
from app.services.item_service import item_service
from app.repositories.item import item_repo
from app.repositories.idempotency_record import idempotency_repo
from app.repositories.location import location_repo
from app.schemas.item import ItemCreate, ItemCreateResponse, ItemHold, ItemPlace, ItemUpdate, ItemResponse
from app.schemas.item_photo import ItemPhotoResponse
from app.core.ai_client import get_ai_client
from app.services.item_photo_service import item_photo_service

router = APIRouter()

@router.post("/analyze")
async def analyze_item_photo(
    *,
    family_id: int = Depends(deps.get_current_family),
    file: UploadFile = File(...)
) -> Any:
    """
    AI 智能拍照录入辅助：上传图片，智能提取物品名、推荐分类/标签与存放位置。
    若系统未配置 AI API Key，或接口调用异常，则返回优雅降级状态（status="disabled" 或 "error"）。
    """
    client = get_ai_client()
    if not client:
        return {
            "status": "disabled",
            "detail": "系统后台未配置 AI API Key，请使用手动录入",
            "result": {
                "name": "",
                "description": "",
                "suggested_location": "",
                "tags": [],
                "confidence": 0.0,
            },
        }

    try:
        image_bytes = await file.read()
        if not image_bytes:
            raise HTTPException(status_code=400, detail="上传图片不能为空")

        result = await client.analyze_image(image_bytes)
        if not result:
            return {
                "status": "error",
                "detail": "AI 未能成功解析图片，请检查网络或配置",
                "result": None
            }

        return {
            "status": "success",
            "detail": "AI 图像分析成功",
            "result": result
        }
    except Exception as e:
        return {
            "status": "error",
            "detail": f"图像处理失败: {str(e)}",
            "result": None
        }


@router.get("/", response_model=List[ItemResponse])
def list_items(
    *,
    db: Session = Depends(deps.get_db),
    family_id: int = Depends(deps.get_current_family),
) -> Any:
    """
    获取当前家庭工作空间下的全部物品。
    """
    return item_repo.get_by_family(db, family_id=family_id)


@router.post("/", response_model=ItemCreateResponse, status_code=status.HTTP_201_CREATED)
def create_item(
    *,
    db: Session = Depends(deps.get_db),
    family_id: int = Depends(deps.get_current_family),
    item_in: ItemCreate,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
) -> Any:
    """
    录入新物品，绑定至特定收纳空间。
    """
    try:
        if idempotency_key:
            record = idempotency_repo.get(
                db,
                family_id=family_id,
                operation="create_item",
                key=idempotency_key,
            )
            if record:
                return JSONResponse(
                    status_code=record.status_code,
                    content=record.response_body,
                )

        item = item_service.create_item(db, obj_in=item_in, family_id=family_id)
        response_body = jsonable_encoder({
            "item": item,
            "location_path": location_repo.get_ancestor_path(
                db, location_id=item.location_id
            ),
        })
        if idempotency_key:
            idempotency_repo.create(
                db,
                family_id=family_id,
                operation="create_item",
                key=idempotency_key,
                status_code=status.HTTP_201_CREATED,
                response_body=response_body,
            )
        return response_body
    except ValueError as e:
        error_message = str(e)
        if "不存在或越权访问" in error_message:
            raise HTTPException(status_code=404, detail=error_message)
        raise HTTPException(status_code=400, detail=error_message)


@router.post("/{item_id}/photos", response_model=ItemPhotoResponse, status_code=status.HTTP_201_CREATED)
async def upload_item_photo(
    *,
    db: Session = Depends(deps.get_db),
    family_id: int = Depends(deps.get_current_family),
    item_id: int,
    file: UploadFile = File(...),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
) -> Any:
    """
    为当前家庭的物品上传图片，图片内容由后端存储管理。
    """
    try:
        if idempotency_key:
            record = idempotency_repo.get(
                db,
                family_id=family_id,
                operation=f"upload_item_photo:{item_id}",
                key=idempotency_key,
            )
            if record:
                return JSONResponse(
                    status_code=record.status_code,
                    content=record.response_body,
                )

        content = await file.read()
        photo = item_photo_service.create_photo(
            db,
            item_id=item_id,
            family_id=family_id,
            filename=file.filename or "photo",
            mime_type=file.content_type or "",
            content=content,
        )
        response_body = jsonable_encoder(photo)
        if idempotency_key:
            idempotency_repo.create(
                db,
                family_id=family_id,
                operation=f"upload_item_photo:{item_id}",
                key=idempotency_key,
                status_code=status.HTTP_201_CREATED,
                response_body=response_body,
            )
        return response_body
    except ValueError as e:
        error_message = str(e)
        if "不存在或越权访问" in error_message:
            raise HTTPException(status_code=404, detail=error_message)
        raise HTTPException(status_code=400, detail=error_message)


@router.get("/{item_id}", response_model=ItemResponse)
def get_item(
    *,
    db: Session = Depends(deps.get_db),
    family_id: int = Depends(deps.get_current_family),
    item_id: int
) -> Any:
    """
    获取单个物品的详细档案。
    """
    try:
        return item_service.get_item(db, item_id=item_id, family_id=family_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{item_id}", response_model=ItemResponse)
def update_item(
    *,
    db: Session = Depends(deps.get_db),
    family_id: int = Depends(deps.get_current_family),
    item_id: int,
    item_in: ItemUpdate,
    if_unmodified_since: Optional[str] = Header(default=None, alias="If-Unmodified-Since"),
) -> Any:
    """
    修改物品属性或挪动其当前位置（支持移入新位置或更换常驻地）。
    """
    try:
        expected_updated_at = _parse_optional_datetime(if_unmodified_since)
        return item_service.update_item(
            db,
            item_id=item_id,
            obj_in=item_in,
            family_id=family_id,
            expected_updated_at=expected_updated_at,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{item_id}", response_model=ItemResponse)
def delete_item(
    *,
    db: Session = Depends(deps.get_db),
    family_id: int = Depends(deps.get_current_family),
    item_id: int
) -> Any:
    """
    删除指定的物品。
    """
    try:
        return item_service.delete_item(db, item_id=item_id, family_id=family_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{item_id}/hold", response_model=ItemResponse)
def hold_item(
    *,
    db: Session = Depends(deps.get_db),
    family_id: int = Depends(deps.get_current_family),
    current_user: User = Depends(deps.get_current_user),
    item_id: int,
    item_in: ItemHold,
    if_unmodified_since: Optional[str] = Header(default=None, alias="If-Unmodified-Since"),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
) -> Any:
    """
    标记物品被当前用户临时拿着，保留拿走前位置。
    """
    try:
        return _run_idempotent_item_action(
            db=db,
            family_id=family_id,
            operation=f"hold_item:{item_id}",
            idempotency_key=idempotency_key,
            action=lambda: item_service.hold_item(
                db,
                item_id=item_id,
                family_id=family_id,
                user_id=current_user.id,
                hold_note=item_in.hold_note,
                expected_updated_at=_parse_optional_datetime(if_unmodified_since),
            ),
        )
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{item_id}/place", response_model=ItemResponse)
def place_item(
    *,
    db: Session = Depends(deps.get_db),
    family_id: int = Depends(deps.get_current_family),
    item_id: int,
    item_in: ItemPlace,
    if_unmodified_since: Optional[str] = Header(default=None, alias="If-Unmodified-Since"),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
) -> Any:
    """
    将物品记录到新的家庭内位置，可选设为默认位置。
    """
    try:
        return _run_idempotent_item_action(
            db=db,
            family_id=family_id,
            operation=f"place_item:{item_id}",
            idempotency_key=idempotency_key,
            action=lambda: item_service.place_item(
                db,
                item_id=item_id,
                family_id=family_id,
                location_id=item_in.location_id,
                set_as_home=item_in.set_as_home,
                expected_updated_at=_parse_optional_datetime(if_unmodified_since),
            ),
        )
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{item_id}/return-home", response_model=ItemResponse)
def return_home(
    *,
    db: Session = Depends(deps.get_db),
    family_id: int = Depends(deps.get_current_family),
    item_id: int,
    if_unmodified_since: Optional[str] = Header(default=None, alias="If-Unmodified-Since"),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
) -> Any:
    """
    将临时拿着或不在默认位置的物品放回默认位置。
    """
    try:
        return _run_idempotent_item_action(
            db=db,
            family_id=family_id,
            operation=f"return_item_home:{item_id}",
            idempotency_key=idempotency_key,
            action=lambda: item_service.return_home(
                db,
                item_id=item_id,
                family_id=family_id,
                expected_updated_at=_parse_optional_datetime(if_unmodified_since),
            ),
        )
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{item_id}/mark-unknown", response_model=ItemResponse)
def mark_unknown(
    *,
    db: Session = Depends(deps.get_db),
    family_id: int = Depends(deps.get_current_family),
    item_id: int,
    if_unmodified_since: Optional[str] = Header(default=None, alias="If-Unmodified-Since"),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
) -> Any:
    """
    标记物品位置待确认，保留上次记录位置。
    """
    try:
        return _run_idempotent_item_action(
            db=db,
            family_id=family_id,
            operation=f"mark_item_unknown:{item_id}",
            idempotency_key=idempotency_key,
            action=lambda: item_service.mark_unknown(
                db,
                item_id=item_id,
                family_id=family_id,
                expected_updated_at=_parse_optional_datetime(if_unmodified_since),
            ),
        )
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


def _parse_optional_datetime(value: Optional[str]) -> Optional[datetime]:
    """
    解析客户端版本时间；缺失时保持旧客户端兼容。
    """
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is not None:
        return parsed.astimezone(tz=None).replace(tzinfo=None)
    return parsed


def _run_idempotent_item_action(
    *,
    db: Session,
    family_id: int,
    operation: str,
    idempotency_key: Optional[str],
    action: Callable[[], Any],
) -> Any:
    if idempotency_key:
        record = idempotency_repo.get(
            db,
            family_id=family_id,
            operation=operation,
            key=idempotency_key,
        )
        if record:
            return JSONResponse(
                status_code=record.status_code,
                content=record.response_body,
            )

    result = action()
    response_body = jsonable_encoder(ItemResponse.model_validate(result))
    if idempotency_key:
        idempotency_repo.create(
            db,
            family_id=family_id,
            operation=operation,
            key=idempotency_key,
            status_code=status.HTTP_200_OK,
            response_body=response_body,
        )
    return response_body


@router.post("/{item_id}/go-home", response_model=ItemResponse)
def item_go_home(
    *,
    db: Session = Depends(deps.get_db),
    family_id: int = Depends(deps.get_current_family),
    item_id: int,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
) -> Any:
    """
    一键归位功能：将临时摆放的物品快速移回设定的常用常驻地。
    """
    try:
        return _run_idempotent_item_action(
            db=db,
            family_id=family_id,
            operation=f"go_home:{item_id}",
            idempotency_key=idempotency_key,
            action=lambda: item_service.go_home(
                db,
                item_id=item_id,
                family_id=family_id,
            ),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
