from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field

class LocationBase(BaseModel):
    name: str
    parent_id: Optional[int] = None

class LocationCreate(LocationBase):
    pass

class LocationUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[int] = None

class LocationResponse(LocationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    family_id: int
    created_at: datetime

class LocationCreateResponse(LocationResponse):
    location_path: List[dict]

# 空间树节点，包含其子节点及直接关联物品数量
class LocationTreeNode(LocationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    family_id: int
    created_at: datetime
    item_count: int = 0
    sub_locations: List['LocationTreeNode'] = Field(default_factory=list)
