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
    locator_hint: Optional[str] = None
    marker_x: Optional[float] = Field(default=None, ge=0, le=1)
    marker_y: Optional[float] = Field(default=None, ge=0, le=1)
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
    locator_hint: Optional[str] = None
    marker_x: Optional[float] = Field(default=None, ge=0, le=1)
    marker_y: Optional[float] = Field(default=None, ge=0, le=1)
    location_id: Optional[int] = None
    home_location_id: Optional[int] = None

class ItemHold(BaseModel):
    hold_note: Optional[str] = None

class ItemPlace(BaseModel):
    location_id: int
    set_as_home: bool = False

class ItemResponse(ItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    family_id: int
    item_status: str = "normal"
    held_by_user_id: Optional[int] = None
    held_by_user_email: Optional[str] = None
    held_at: Optional[datetime] = None
    hold_note: Optional[str] = None
    last_location_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    photos: List[ItemPhotoResponse] = Field(default_factory=list)

class ItemCreateResponse(BaseModel):
    item: ItemResponse
    location_path: List[dict]
