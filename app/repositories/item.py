from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, String
from app.repositories.base import BaseRepository
from app.models.item import Item
from app.schemas.item import ItemCreate, ItemUpdate

class ItemRepository(BaseRepository[Item, ItemCreate, ItemUpdate]):
    def get_by_family(
        self, db: Session, *, family_id: int, location_id: Optional[int] = None, skip: int = 0, limit: int = 100
    ) -> List[Item]:
        query = db.query(self.model).filter(self.model.family_id == family_id)
        if location_id is not None:
            query = query.filter(self.model.location_id == location_id)
        return query.offset(skip).limit(limit).all()

    def get_by_location_ids(
        self, db: Session, *, family_id: int, location_ids: List[int], skip: int = 0, limit: int = 100
    ) -> List[Item]:
        return db.query(self.model).filter(
            self.model.family_id == family_id,
            self.model.location_id.in_(location_ids),
        ).offset(skip).limit(limit).all()

    def create_in_family(self, db: Session, *, obj_in: ItemCreate, family_id: int) -> Item:
        db_obj = Item(
            name=obj_in.name,
            description=obj_in.description,
            quantity=obj_in.quantity,
            tags=obj_in.tags or [],
            photo_url=None,
            locator_hint=obj_in.locator_hint,
            marker_x=obj_in.marker_x,
            marker_y=obj_in.marker_y,
            item_status="normal",
            location_id=obj_in.location_id,
            home_location_id=obj_in.home_location_id,
            family_id=family_id
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def global_search(
        self, db: Session, *, family_id: int, q: str, limit: int = 30
    ) -> List[Item]:
        """
        全文模糊匹配名称、标签、描述以及所在空间的名称，限定在该家庭工作空间内
        """
        from app.models.location import Location
        from app.repositories.location import location_repo
        like_q = f"%{q}%"
        direct_matches = db.query(self.model).join(
            Location, self.model.location_id == Location.id
        ).filter(
            self.model.family_id == family_id
        ).filter(
            or_(
                self.model.name.ilike(like_q),
                self.model.description.ilike(like_q),
                # JSON 类型的模糊查找，SQLite 默认将 JSON 作为 Text 存储，可以直接使用 ilike 进行查询
                func.cast(self.model.tags, String).ilike(like_q),
                Location.name.ilike(like_q)
            )
        ).order_by(self.model.id.asc()).limit(limit).all()

        matched_by_id = {item.id: item for item in direct_matches}
        remaining = limit - len(matched_by_id)
        if remaining <= 0:
            return list(matched_by_id.values())

        q_lower = q.lower()
        locations = location_repo.get_all_family_locations(db, family_id=family_id)
        locations_by_id = {location.id: location for location in locations}
        matching_location_ids = []
        for location in locations:
            current = location
            while current is not None:
                if q_lower in current.name.lower():
                    matching_location_ids.append(location.id)
                    break
                current = locations_by_id.get(current.parent_id)

        if matching_location_ids:
            path_matches = db.query(self.model).filter(
                self.model.family_id == family_id,
                self.model.location_id.in_(matching_location_ids),
                ~self.model.id.in_(matched_by_id.keys()) if matched_by_id else True,
            ).order_by(self.model.id.asc()).limit(remaining).all()
            matched_by_id.update({item.id: item for item in path_matches})
        return list(matched_by_id.values())

item_repo = ItemRepository(Item)
