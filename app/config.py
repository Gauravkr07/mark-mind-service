from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    # Postgres
    database_url: str = "postgresql+asyncpg://mm_user:mm_password@postgres:5432/mm_careers"

    @field_validator("database_url")
    @classmethod
    def _use_asyncpg_driver(cls, v: str) -> str:
        # Managed Postgres providers (e.g. Render) hand out plain
        # postgres:// / postgresql:// URLs; SQLAlchemy's async engine needs
        # the asyncpg driver explicitly in the scheme.
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    # Admin auth (simple header-based key; swap for JWT/RBAC later if needed)
    admin_api_key: str = "change-me-in-.env"

    # Uploads
    upload_dir: str = "/app/uploads"
    max_upload_mb: int = 5
    allowed_resume_types: tuple = (".pdf", ".doc", ".docx")

    # Rate limiting (applications per email per job, per window)
    apply_rate_limit_count: int = 3
    apply_rate_limit_window_seconds: int = 3600  # 1 hour

    # CORS
    allowed_origins: list[str] = ["http://localhost:3000", "https://markandmind.example.com"]

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
