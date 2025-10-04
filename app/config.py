from typing import Annotated, List, Union
from pydantic import BeforeValidator, field_validator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        env_file_encoding="utf-8",
    )

    # CORS
    ORIGINAL_CORS_ALLOWED_ORIGINS: str = Field(
        default="*", alias="CORS_ALLOWED_ORIGINS"
    )

    # Database
    POSTGRESQL_USER: str
    POSTGRESQL_PASSWORD: str
    POSTGRESQL_HOST: str = "localhost"
    POSTGRESQL_PORT: str = "5432"
    POSTGRESQL_DATABASE: str

    # Redis
    REDIS_URL: str

    # OpenRouter
    OPENROUTER_API_KEY: str
    OPENROUTER_MODEL: str = "x-ai/grok-4-fast:free"

    # Application
    APP_ENV: str = "development"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Upload
    MAX_FILE_SIZE: int = 10485760  # 10MB
    UPLOAD_DIR: str = "./uploads"
    REFERENCE_DOCS_DIR: str = "./reference_docs"

    # ChromaDB
    CHROMA_PERSIST_DIR: str = "./chroma_db"

    # Celery
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    @property
    def CORS_ALLOWED_ORIGINS(self) -> List[str]:
        if self.ORIGINAL_CORS_ALLOWED_ORIGINS.strip() == "*":
            return ["*"]
        return [
            origin.strip()
            for origin in self.ORIGINAL_CORS_ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
