from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from app.repositories.item import item_repo
from app.repositories.location import location_repo
from app.models.item import Item
from app.schemas.item import ItemCreate, ItemUpdate
from app.services.item_photo_service import item_photo_service

class ItemService:
    def create_item(self, db: Session, *, obj_in: ItemCreate, family_id: int) -> Item:
        """
        在指定家庭创建新物品，验证空间位置是否合法
        """
        # 1. 验证目标位置存在且属于同一家庭
        loc = location_repo.get(db, id=obj_in.location_id)
        if not loc or loc.family_id != family_id:
            raise ValueError("物品存放位置非法或不属于该家庭")

        # 2. 如果指定了常住地，也验证其合法性
        if obj_in.home_location_id:
            home_loc = location_repo.get(db, id=obj_in.home_location_id)
            if not home_loc or home_loc.family_id != family_id:
                raise ValueError("物品常驻位置非法或不属于该家庭")

        return item_repo.create_in_family(db, obj_in=obj_in, family_id=family_id)

    def update_item(
        self,
        db: Session,
        *,
        item_id: int,
        obj_in: ItemUpdate,
        family_id: int,
        expected_updated_at: Optional[datetime] = None,
    ) -> Item:
        """
        更新物品，包括位置调整校验
        """
        db_obj = item_repo.get(db, id=item_id)
        if not db_obj or db_obj.family_id != family_id:
            raise ValueError("物品不存在或越权访问")
        if expected_updated_at is not None and db_obj.updated_at > expected_updated_at:
            raise RuntimeError("服务端记录已更新，请先刷新后再保存")

        # 校验新存放位置
        if obj_in.location_id is not None:
            loc = location_repo.get(db, id=obj_in.location_id)
            if not loc or loc.family_id != family_id:
                raise ValueError("新存放位置非法")

        # 校验新常驻位置
        if obj_in.home_location_id is not None:
            home_loc = location_repo.get(db, id=obj_in.home_location_id)
            if not home_loc or home_loc.family_id != family_id:
                raise ValueError("新常驻位置非法")

        update_data = obj_in.model_dump(exclude_unset=True)
        update_data.pop("photo_url", None)
        if "location_id" in update_data or "home_location_id" in update_data:
            update_data.setdefault("item_status", "normal")
            update_data.setdefault("held_by_user_id", None)
            update_data.setdefault("held_at", None)
            update_data.setdefault("hold_note", None)
        if (
            "location_id" in update_data
            and update_data["location_id"] != db_obj.location_id
            and "marker_x" not in update_data
            and "marker_y" not in update_data
        ):
            update_data["marker_x"] = None
            update_data["marker_y"] = None
        return item_repo.update(db, db_obj=db_obj, obj_in=update_data)

    def hold_item(
        self,
        db: Session,
        *,
        item_id: int,
        family_id: int,
        user_id: int,
        hold_note: Optional[str] = None,
        expected_updated_at: Optional[datetime] = None,
    ) -> Item:
        """
        将物品标记为当前用户临时拿着，并保留拿走前位置作为找物线索。
        """
        db_obj = self._get_family_item(db, item_id=item_id, family_id=family_id)
        self._check_version(db_obj, expected_updated_at)
        return item_repo.update(
            db,
            db_obj=db_obj,
            obj_in={
                "item_status": "holding",
                "held_by_user_id": user_id,
                "held_at": datetime.utcnow(),
                "hold_note": hold_note,
                "last_location_id": db_obj.location_id,
            },
        )

    def place_item(
        self,
        db: Session,
        *,
        item_id: int,
        family_id: int,
        location_id: int,
        set_as_home: bool = False,
        expected_updated_at: Optional[datetime] = None,
    ) -> Item:
        """
        将物品记录到一个家庭内位置，可选同步更新默认位置。
        """
        db_obj = self._get_family_item(db, item_id=item_id, family_id=family_id)
        self._check_version(db_obj, expected_updated_at)
        loc = location_repo.get(db, id=location_id)
        if not loc or loc.family_id != family_id:
            raise ValueError("新存放位置非法")

        update_data = {
            "location_id": location_id,
            "item_status": "normal",
            "held_by_user_id": None,
            "held_at": None,
            "hold_note": None,
            "last_location_id": None,
            "marker_x": None,
            "marker_y": None,
        }
        if set_as_home:
            update_data["home_location_id"] = location_id
        return item_repo.update(db, db_obj=db_obj, obj_in=update_data)

    def mark_unknown(
        self,
        db: Session,
        *,
        item_id: int,
        family_id: int,
        expected_updated_at: Optional[datetime] = None,
    ) -> Item:
        """
        标记现有位置不可信，同时保留上次记录位置。
        """
        db_obj = self._get_family_item(db, item_id=item_id, family_id=family_id)
        self._check_version(db_obj, expected_updated_at)
        return item_repo.update(
            db,
            db_obj=db_obj,
            obj_in={
                "item_status": "unknown",
                "held_by_user_id": None,
                "held_at": None,
                "hold_note": None,
                "last_location_id": db_obj.location_id,
            },
        )

    def return_home(
        self,
        db: Session,
        *,
        item_id: int,
        family_id: int,
        expected_updated_at: Optional[datetime] = None,
    ) -> Item:
        """
        将临时拿着或放错位置的物品放回默认位置。
        """
        db_obj = self._get_family_item(db, item_id=item_id, family_id=family_id)
        self._check_version(db_obj, expected_updated_at)
        target_location_id = db_obj.home_location_id or db_obj.last_location_id
        if not target_location_id:
            raise ValueError("该物品未设置默认位置")
        target_location = location_repo.get(db, id=target_location_id)
        if not target_location or target_location.family_id != family_id:
            raise ValueError("默认位置不存在或不属于该家庭")
        if db_obj.item_status == "normal" and db_obj.location_id == target_location_id:
            raise ValueError("物品已在默认位置")
        return item_repo.update(
            db,
            db_obj=db_obj,
            obj_in={
                "location_id": target_location_id,
                "item_status": "normal",
                "held_by_user_id": None,
                "held_at": None,
                "hold_note": None,
                "last_location_id": None,
                "marker_x": None,
                "marker_y": None,
            },
        )

    def go_home(self, db: Session, *, item_id: int, family_id: int) -> Item:
        """
        一键归位功能：将物品的当前位置 location_id 重置为其设定的常用常驻地 home_location_id
        """
        return self.return_home(db, item_id=item_id, family_id=family_id)

    def delete_item(self, db: Session, *, item_id: int, family_id: int) -> Item:
        """
        删除物品
        """
        db_obj = item_repo.get(db, id=item_id)
        if not db_obj or db_obj.family_id != family_id:
            raise ValueError("物品不存在或越权访问")

        item_photo_service.delete_photos_for_item(db, item_id=item_id, family_id=family_id)
        return item_repo.remove(db, id=item_id)

    def get_item(self, db: Session, *, item_id: int, family_id: int) -> Item:
        """
        获取单件物品详情
        """
        db_obj = item_repo.get(db, id=item_id)
        if not db_obj or db_obj.family_id != family_id:
            raise ValueError("物品不存在或越权访问")
        return db_obj

    def _get_family_item(self, db: Session, *, item_id: int, family_id: int) -> Item:
        db_obj = item_repo.get(db, id=item_id)
        if not db_obj or db_obj.family_id != family_id:
            raise ValueError("物品不存在或越权访问")
        return db_obj

    def _check_version(self, db_obj: Item, expected_updated_at: Optional[datetime]) -> None:
        if expected_updated_at is not None and db_obj.updated_at > expected_updated_at:
            raise RuntimeError("服务端记录已更新，请先刷新后再保存")

item_service = ItemService()
