from typing import Any, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.api import deps
from app.repositories.item import item_repo
from app.repositories.location import location_repo
from app.schemas.item import ItemResponse

router = APIRouter()

class SearchResult(BaseModel):
    item: ItemResponse
    location_path: List[dict]  # 从根节点到当前节点路径的面包屑，例如 [{"id":1, "name":"客厅"}]

@router.get("/", response_model=List[SearchResult])
def search(
    *,
    db: Session = Depends(deps.get_db),
    family_id: int = Depends(deps.get_current_family),
    q: str = Query(..., description="要搜索的关键字"),
    limit: int = Query(30, ge=1, le=50, description="最大返回结果数"),
) -> Any:
    """
    全局物品智能检索：支持匹配物品名、描述、标签及所属空间名，并自动解析每件物品的空间面包屑路径。
    """
    if not q.strip():
        return []

    # 1. 查找匹配的物品
    items = item_repo.global_search(db, family_id=family_id, q=q.strip(), limit=limit)

    # 2. 批量解析面包屑路径，避免搜索结果逐条递归查询。
    paths_by_location = location_repo.get_paths_for_locations(
        db,
        family_id=family_id,
        location_ids=[item.location_id for item in items],
    )
    results = []
    for item in items:
        results.append({
            "item": item,
            "location_path": paths_by_location.get(item.location_id, [])
        })

    return results
