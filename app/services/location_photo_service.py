from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import settings
from app.repositories.location import location_repo
from app.repositories.location_photo import location_photo_repo
from app.services.storage_service import get_storage_service


class LocationPhotoService:
    def create_photo(
        self,
        db: Session,
        *,
        location_id: int,
        family_id: int,
        filename: str,
        mime_type: str,
        content: bytes,
    ):
        """
        校验家庭权限并保存空间定位照片。
        """
        location = location_repo.get(db, id=location_id)
        if not location or location.family_id != family_id:
            raise ValueError("空间不存在或越权访问")
        self._validate_upload(mime_type=mime_type, content=content)

        storage_key = self._build_storage_key(
            family_id=family_id,
            location_id=location_id,
            filename=filename,
            mime_type=mime_type,
        )
        storage = get_storage_service()
        storage.save(storage_key=storage_key, content=content)
        try:
            photo = location_photo_repo.create(
                db,
                location_id=location_id,
                family_id=family_id,
                storage_provider=settings.STORAGE_PROVIDER,
                storage_key=storage_key,
                mime_type=mime_type,
                size_bytes=len(content),
            )
            location.locator_photo_id = photo.id
            db.add(location)
            db.commit()
            db.refresh(photo)
            return photo
        except Exception:
            storage.delete(storage_key=storage_key)
            raise

    def get_photo_content(self, db: Session, *, photo_id: int, family_id: int):
        """
        读取属于当前家庭的空间定位照片内容。
        """
        photo = location_photo_repo.get(db, photo_id=photo_id)
        if not photo or photo.family_id != family_id:
            raise ValueError("图片不存在或越权访问")
        try:
            content = get_storage_service().read(storage_key=photo.storage_key)
        except FileNotFoundError:
            raise ValueError("图片不存在或越权访问") from None
        return photo, content

    def delete_photo(self, db: Session, *, photo_id: int, family_id: int):
        """
        删除当前家庭的单张空间定位照片，并清理引用它的空间。
        """
        photo = location_photo_repo.get(db, photo_id=photo_id)
        if not photo or photo.family_id != family_id:
            raise ValueError("图片不存在或越权访问")
        location = location_repo.get(db, id=photo.location_id)
        if location and location.family_id == family_id and location.locator_photo_id == photo.id:
            location.locator_photo_id = None
            db.add(location)
        get_storage_service().delete(storage_key=photo.storage_key)
        removed = location_photo_repo.remove(db, photo=photo)
        db.commit()
        return removed

    def _validate_upload(self, *, mime_type: str, content: bytes) -> None:
        """
        校验上传内容大小和 MIME 类型。
        """
        if not content:
            raise ValueError("上传图片不能为空")
        if len(content) > settings.MAX_PHOTO_UPLOAD_BYTES:
            raise ValueError("上传图片过大")
        if mime_type not in settings.allowed_photo_mime_types():
            raise ValueError("仅支持上传图片文件")

    def _build_storage_key(
        self, *, family_id: int, location_id: int, filename: str, mime_type: str
    ) -> str:
        """
        为空间定位照片生成稳定分层 key，避免暴露客户端原始文件名。
        """
        extension = Path(filename).suffix.lower()
        if not extension:
            extension = {
                "image/jpeg": ".jpg",
                "image/png": ".png",
                "image/webp": ".webp",
            }.get(mime_type, ".bin")
        return f"locations/{family_id}/{location_id}/{uuid4().hex}{extension}"


location_photo_service = LocationPhotoService()
