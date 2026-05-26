from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.item_photo import ItemPhotoResponse

class ItemBase(BaseModel):
    name: str
    description: Optional[str] = None
    quantity: Optional[int] = 1
    tags: Optional[List[str]] = Field(default_factory=list)
    photo_url: Optional[str] = None
    location_id: int
    home_location_id: Optional[int] = None

class ItemCreate(ItemBase):
    pass

class ItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    quantity: Optional[int] = None
    tags: Optional[List[str]] = None
    photo_url: Optional[str] = None
    location_id: Optional[int] = None
    home_location_id: Optional[int] = None

class ItemResponse(ItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    family_id: int
    created_at: datetime
    updated_at: datetime
    photos: List[ItemPhotoResponse] = Field(default_factory=list)

class ItemCreateResponse(BaseModel):
    item: ItemResponse
    location_path: List[dict]
