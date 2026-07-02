from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    CORE_BACKEND_URL: str = "http://localhost:8001"
    # BD del nucleo bancario para el puente de promocion (sync_outbox -> core)
    CORE_DATABASE_URL: str = (
        "postgresql://neondb_owner:npg_5Ks8vdXuWfTP@ep-young-band-atjrkvnz-pooler.c-9.us-east-1.aws.neon.tech/bd_core_financiero?sslmode=require"
    )
    PORT: int = 8003

    class Config:
        env_file = ".env"

settings = Settings()
