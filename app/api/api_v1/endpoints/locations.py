from typing import Any, List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api import deps
from app.repositories.idempotency_record import idempotency_repo
from app.services.location_service import location_service
from app.repositories.location import location_repo
from app.repositories.item import item_repo
from app.schemas.location import (
    LocationCreate,
    LocationCreateResponse,
    LocationUpdate,
    LocationResponse,
    LocationTreeNode,
)
from app.schemas.item import ItemResponse

router = APIRouter()

@router.post("/", response_model=LocationCreateResponse, status_code=status.HTTP_201_CREATED)
def create_location(
    *,
    db: Session = Depends(deps.get_db),
    family_id: int = Depends(deps.get_current_family),
    location_in: LocationCreate,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
) -> Any:
    """
    创建一个新的收纳空间，支持嵌套。
    """
    try:
        if idempotency_key:
            record = idempotency_repo.get(
                db,
                family_id=family_id,
                operation="create_location",
                key=idempotency_key,
            )
            if record:
                return JSONResponse(
                    status_code=record.status_code,
                    content=record.response_body,
                )

        location = location_service.create_location(db, obj_in=location_in, family_id=family_id)
        response_body = jsonable_encoder({
            "id": location.id,
            "name": location.name,
            "parent_id": location.parent_id,
            "family_id": location.family_id,
            "created_at": location.created_at,
            "location_path": location_repo.get_ancestor_path(
                db, location_id=location.id
            ),
        })
        if idempotency_key:
            idempotency_repo.create(
                db,
                family_id=family_id,
                operation="create_location",
                key=idempotency_key,
                status_code=status.HTTP_201_CREATED,
                response_body=response_body,
            )
        return response_body
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tree", response_model=List[LocationTreeNode])
def get_location_tree(
    *,
    db: Session = Depends(deps.get_db),
    family_id: int = Depends(deps.get_current_family)
) -> Any:
    """
    以折叠树形结构返回当前家庭的所有空间（包含每个空间的物品计数）。
    """
    return location_service.get_location_tree(db, family_id=family_id)


@router.get("/{location_id}", response_model=LocationResponse)
def get_location(
    *,
    db: Session = Depends(deps.get_db),
    family_id: int = Depends(deps.get_current_family),
    location_id: int
) -> Any:
    """
    获取单个空间的详细信息。
    """
    loc = location_repo.get(db, id=location_id)
    if not loc or loc.family_id != family_id:
        raise HTTPException(status_code=404, detail="空间位置不存在")
    return loc


@router.put("/{location_id}", response_model=LocationResponse)
def update_location(
    *,
    db: Session = Depends(deps.get_db),
    family_id: int = Depends(deps.get_current_family),
    location_id: int,
    location_in: LocationUpdate
) -> Any:
    """
    更新收纳空间信息（例如修改名称或拖动换父空间）。
    """
    try:
        return location_service.update_location(
            db, location_id=location_id, obj_in=location_in, family_id=family_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{location_id}", response_model=LocationResponse)
def delete_location(
    *,
    db: Session = Depends(deps.get_db),
    family_id: int = Depends(deps.get_current_family),
    location_id: int
) -> Any:
    """
    删除指定的收纳空间（级联删除旗下所有子空间和物品）。
    """
    try:
        return location_service.delete_location(db, location_id=location_id, family_id=family_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{location_id}/items", response_model=List[ItemResponse])
def get_location_items(
    *,
    db: Session = Depends(deps.get_db),
    family_id: int = Depends(deps.get_current_family),
    location_id: int
) -> Any:
    """
    获取指定收纳空间及其所有子空间内的物品列表。
    """
    loc = location_repo.get(db, id=location_id)
    if not loc or loc.family_id != family_id:
        raise HTTPException(status_code=404, detail="空间位置不存在")

    location_ids = location_repo.get_descendant_ids(db, location_id=location_id)
    return item_repo.get_by_location_ids(
        db, family_id=family_id, location_ids=location_ids
    )


@router.get("/{location_id}/path", response_model=List[dict])
def get_location_path(
    *,
    db: Session = Depends(deps.get_db),
    family_id: int = Depends(deps.get_current_family),
    location_id: int
) -> Any:
    """
    递归获取当前空间的面包屑路径列表，从根节点到叶节点。
    """
    loc = location_repo.get(db, id=location_id)
    if not loc or loc.family_id != family_id:
        raise HTTPException(status_code=404, detail="空间位置不存在")

    return location_repo.get_ancestor_path(db, location_id=location_id)
