import pytest
from pydantic import ValidationError

from app.core.config import DEFAULT_SECRET_KEY, Settings
from app.services.storage_service import LocalStorageService


def test_default_local_storage_root_uses_data_uploads():
    settings = Settings()

    assert settings.LOCAL_STORAGE_ROOT == "./data/uploads"


def test_local_storage_rejects_path_traversal(tmp_path):
    storage = LocalStorageService(str(tmp_path / "uploads"))

    with pytest.raises(ValueError, match="非法存储路径"):
        storage.save(storage_key="../escape.jpg", content=b"bad")


def test_production_rejects_default_secret_key():
    with pytest.raises(ValidationError, match="生产环境必须通过 SECRET_KEY 配置安全密钥"):
        Settings(ENVIRONMENT="production", SECRET_KEY=DEFAULT_SECRET_KEY)


def test_production_rejects_short_secret_key():
    with pytest.raises(ValidationError, match="生产环境 SECRET_KEY 长度必须至少 32 字节"):
        Settings(ENVIRONMENT="production", SECRET_KEY="short-secret")


def test_production_accepts_long_secret_key():
    settings = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="a-long-random-secret-with-32-bytes",
    )

    assert settings.SECRET_KEY == "a-long-random-secret-with-32-bytes"
