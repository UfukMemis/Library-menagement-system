from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://lms_user:lms_password@localhost:5432/library_db"
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    cors_origins: str = "http://localhost:8080,http://localhost:3000"
    admin_email: str = "admin@library.local"
    admin_password: str = "Admin123!"
    borrow_days: int = 14
    max_borrows_per_user: int = 5
    upload_dir: str = "uploads"

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def upload_path(self):
        from pathlib import Path

        path = Path(self.upload_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()
