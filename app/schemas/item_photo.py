from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ItemPhotoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    item_id: int
    family_id: int
    storage_provider: str
    storage_key: str
    mime_type: str
    size_bytes: int
    created_at: datetime
