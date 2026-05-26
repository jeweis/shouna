from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.item_photo import ItemPhoto
from app.repositories.item import item_repo
from app.repositories.item_photo import item_photo_repo
from app.services.storage_service import get_storage_service


class ItemPhotoService:
    def create_photo(
        self,
        db: Session,
        *,
        item_id: int,
        family_id: int,
        filename: str,
        mime_type: str,
        content: bytes,
    ) -> ItemPhoto:
        """
        校验家庭权限并保存物品图片。
        """
        item = item_repo.get(db, id=item_id)
        if not item or item.family_id != family_id:
            raise ValueError("物品不存在或越权访问")
        self._validate_upload(mime_type=mime_type, content=content)

        storage_key = self._build_storage_key(
            family_id=family_id,
            item_id=item_id,
            filename=filename,
            mime_type=mime_type,
        )
        storage = get_storage_service()
        storage.save(storage_key=storage_key, content=content)
        try:
            return item_photo_repo.create(
                db,
                item_id=item_id,
                family_id=family_id,
                storage_provider=settings.STORAGE_PROVIDER,
                storage_key=storage_key,
                mime_type=mime_type,
                size_bytes=len(content),
            )
        except Exception:
            storage.delete(storage_key=storage_key)
            raise

    def get_photo_content(self, db: Session, *, photo_id: int, family_id: int) -> tuple[ItemPhoto, bytes]:
        """
        读取属于当前家庭的图片内容。
        """
        photo = item_photo_repo.get(db, photo_id=photo_id)
        if not photo or photo.family_id != family_id:
            raise ValueError("图片不存在或越权访问")
        try:
            content = get_storage_service().read(storage_key=photo.storage_key)
        except FileNotFoundError:
            raise ValueError("图片不存在或越权访问") from None
        return photo, content

    def delete_photo(self, db: Session, *, photo_id: int, family_id: int) -> ItemPhoto:
        """
        删除单张属于当前家庭的图片文件和元数据。
        """
        photo = item_photo_repo.get(db, photo_id=photo_id)
        if not photo or photo.family_id != family_id:
            raise ValueError("图片不存在或越权访问")
        get_storage_service().delete(storage_key=photo.storage_key)
        return item_photo_repo.remove(db, photo=photo)

    def delete_photos_for_item(self, db: Session, *, item_id: int, family_id: int) -> None:
        """
        删除物品下全部图片的文件与元数据。
        """
        photos = item_photo_repo.get_by_item(db, item_id=item_id, family_id=family_id)
        storage = get_storage_service()
        for photo in photos:
            storage.delete(storage_key=photo.storage_key)
            db.delete(photo)
        db.commit()

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
        self, *, family_id: int, item_id: int, filename: str, mime_type: str
    ) -> str:
        """
        为本地存储生成稳定分层 key，隐藏客户端原始长文件名。
        """
        extension = Path(filename).suffix.lower()
        if not extension:
            extension = {
                "image/jpeg": ".jpg",
                "image/png": ".png",
                "image/webp": ".webp",
            }.get(mime_type, ".bin")
        return f"items/{family_id}/{item_id}/{uuid4().hex}{extension}"


item_photo_service = ItemPhotoService()
