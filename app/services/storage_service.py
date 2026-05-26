from pathlib import Path
from typing import Protocol

from app.core.config import settings


class StorageService(Protocol):
    """
    图片存储服务接口，方便后续替换为对象存储。
    """

    def save(self, *, storage_key: str, content: bytes) -> None:
        """保存文件内容。"""

    def read(self, *, storage_key: str) -> bytes:
        """读取文件内容。"""

    def delete(self, *, storage_key: str) -> None:
        """删除文件内容。"""


class LocalStorageService:
    def __init__(self, root: str):
        """
        使用本地目录保存上传文件，所有 key 都会限制在 root 内部。
        """
        self.root = Path(root)

    def _resolve_key(self, storage_key: str) -> Path:
        """
        将逻辑 key 转换为安全的本地路径，避免路径穿越。
        """
        root = self.root.resolve()
        target = (self.root / storage_key).resolve()
        if target != root and root not in target.parents:
            raise ValueError("非法存储路径")
        return target

    def save(self, *, storage_key: str, content: bytes) -> None:
        """
        保存文件内容。
        """
        target = self._resolve_key(storage_key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)

    def read(self, *, storage_key: str) -> bytes:
        """
        读取文件内容。
        """
        target = self._resolve_key(storage_key)
        if not target.exists():
            raise FileNotFoundError(storage_key)
        return target.read_bytes()

    def delete(self, *, storage_key: str) -> None:
        """
        删除文件内容，文件不存在时保持幂等。
        """
        target = self._resolve_key(storage_key)
        if target.exists():
            target.unlink()


def get_storage_service() -> StorageService:
    """
    返回当前配置的存储服务实例。
    """
    if settings.STORAGE_PROVIDER != "local":
        raise ValueError("当前仅支持本地图片存储")
    return LocalStorageService(settings.LOCAL_STORAGE_ROOT)
