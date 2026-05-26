from fastapi import APIRouter
from app.api.api_v1.endpoints import auth, families, item_photos, items, locations, search

api_router = APIRouter()

# 挂载各个核心业务路由
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(families.router, prefix="/families", tags=["families"])
api_router.include_router(locations.router, prefix="/locations", tags=["locations"])
api_router.include_router(items.router, prefix="/items", tags=["items"])
api_router.include_router(item_photos.router, prefix="/item-photos", tags=["item-photos"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
