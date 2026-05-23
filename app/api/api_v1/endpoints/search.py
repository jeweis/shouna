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
    q: str = Query(..., description="要搜索的关键字")
) -> Any:
    """
    全局物品智能检索：支持匹配物品名、描述、标签及所属空间名，并自动解析每件物品的空间面包屑路径。
    """
    if not q.strip():
        return []

    # 1. 查找匹配的物品
    items = item_repo.global_search(db, family_id=family_id, q=q.strip())

    # 2. 为每个物品递归解析面包屑路径
    results = []
    for item in items:
        path = location_repo.get_ancestor_path(db, location_id=item.location_id)
        results.append({
            "item": item,
            "location_path": path
        })

    return results
