from typing import List

from sqlalchemy.orm import Session

from app.models.location_photo import LocationPhoto


class LocationPhotoRepository:
    def get(self, db: Session, *, photo_id: int) -> LocationPhoto | None:
        """
        根据主键读取空间定位照片元数据。
        """
        return db.get(LocationPhoto, photo_id)

    def get_by_location(self, db: Session, *, location_id: int, family_id: int) -> List[LocationPhoto]:
        """
        读取某个家庭空间下的全部定位照片元数据。
        """
        return (
            db.query(LocationPhoto)
            .filter(LocationPhoto.location_id == location_id, LocationPhoto.family_id == family_id)
            .all()
        )

    def create(
        self,
        db: Session,
        *,
        location_id: int,
        family_id: int,
        storage_provider: str,
        storage_key: str,
        mime_type: str,
        size_bytes: int,
    ) -> LocationPhoto:
        """
        写入空间定位照片元数据，二进制内容由存储服务负责。
        """
        db_obj = LocationPhoto(
            location_id=location_id,
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

    def remove(self, db: Session, *, photo: LocationPhoto) -> LocationPhoto:
        """
        删除空间定位照片元数据。
        """
        db.delete(photo)
        db.commit()
        return photo


location_photo_repo = LocationPhotoRepository()
