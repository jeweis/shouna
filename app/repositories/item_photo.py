from typing import List

from sqlalchemy.orm import Session

from app.models.item_photo import ItemPhoto


class ItemPhotoRepository:
    def get(self, db: Session, *, photo_id: int) -> ItemPhoto | None:
        """
        根据主键读取物品图片元数据。
        """
        return db.get(ItemPhoto, photo_id)

    def get_by_item(self, db: Session, *, item_id: int, family_id: int) -> List[ItemPhoto]:
        """
        读取某个家庭物品下的全部图片元数据。
        """
        return (
            db.query(ItemPhoto)
            .filter(ItemPhoto.item_id == item_id, ItemPhoto.family_id == family_id)
            .all()
        )

    def create(
        self,
        db: Session,
        *,
        item_id: int,
        family_id: int,
        storage_provider: str,
        storage_key: str,
        mime_type: str,
        size_bytes: int,
    ) -> ItemPhoto:
        """
        写入图片元数据，实际二进制内容由存储服务负责。
        """
        db_obj = ItemPhoto(
            item_id=item_id,
            family_id=family_id,
            storage_provider=storage_provider,
            storage_key=storage_key,
            mime_type=mime_type,
            size_bytes=size_bytes,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, photo: ItemPhoto) -> ItemPhoto:
        """
        删除图片元数据。
        """
        db.delete(photo)
        db.commit()
        return photo


item_photo_repo = ItemPhotoRepository()
