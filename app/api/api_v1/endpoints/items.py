from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session

from app.api import deps
from app.services.item_service import item_service
from app.repositories.item import item_repo
from app.repositories.location import location_repo
from app.schemas.item import ItemCreate, ItemCreateResponse, ItemUpdate, ItemResponse
from app.core.ai_client import get_ai_client

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
    item_in: ItemCreate
) -> Any:
    """
    录入新物品，绑定至特定收纳空间。
    """
    try:
        item = item_service.create_item(db, obj_in=item_in, family_id=family_id)
        return {
            "item": item,
            "location_path": location_repo.get_ancestor_path(
                db, location_id=item.location_id
            ),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


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
    item_in: ItemUpdate
) -> Any:
    """
    修改物品属性或挪动其当前位置（支持移入新位置或更换常驻地）。
    """
    try:
        return item_service.update_item(db, item_id=item_id, obj_in=item_in, family_id=family_id)
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


@router.post("/{item_id}/go-home", response_model=ItemResponse)
def item_go_home(
    *,
    db: Session = Depends(deps.get_db),
    family_id: int = Depends(deps.get_current_family),
    item_id: int
) -> Any:
    """
    一键归位功能：将临时摆放的物品快速移回设定的常用常驻地。
    """
    try:
        return item_service.go_home(db, item_id=item_id, family_id=family_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
