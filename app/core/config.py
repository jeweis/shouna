import os
from typing import Optional
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SECRET_KEY = "shouna_super_secret_key_change_me_in_production"


class Settings(BaseSettings):
    PROJECT_NAME: str = "shouna"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = DEFAULT_SECRET_KEY
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    BACKEND_CORS_ORIGINS: list[str] = []
    BACKEND_CORS_ALLOW_ORIGIN_REGEX: Optional[str] = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"

    # 数据库配置，默认使用本地 SQLite 数据库文件
    DATABASE_URL: str = "sqlite:///./shouna.db"

    # AI 模块配置
    # AI_PROVIDER 可以是 'openai' 或 'anthropic'，留空代表禁用 AI 智能录入
    AI_PROVIDER: Optional[str] = None
    AI_API_KEY: Optional[str] = None
    AI_BASE_URL: Optional[str] = None
    AI_MODEL: Optional[str] = None

    # 图片存储配置。先使用本地文件系统，后续可在 StorageService 层替换为对象存储。
    STORAGE_PROVIDER: str = "local"
    LOCAL_STORAGE_ROOT: str = "./data/uploads"
    MAX_PHOTO_UPLOAD_BYTES: int = 5 * 1024 * 1024
    ALLOWED_PHOTO_MIME_TYPES: str = "image/jpeg,image/png,image/webp"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )

    @model_validator(mode="after")
    def require_production_secret(self):
        if self.ENVIRONMENT.lower() not in {"prod", "production"}:
            return self
        if self.SECRET_KEY == DEFAULT_SECRET_KEY:
            raise ValueError("生产环境必须通过 SECRET_KEY 配置安全密钥")
        if len(self.SECRET_KEY.encode("utf-8")) < 32:
            raise ValueError("生产环境 SECRET_KEY 长度必须至少 32 字节")
        return self

    def allowed_photo_mime_types(self) -> set[str]:
        """
        返回允许上传的图片 MIME 类型集合。
        """
        return {
            mime_type.strip()
            for mime_type in self.ALLOWED_PHOTO_MIME_TYPES.split(",")
            if mime_type.strip()
        }

settings = Settings()
