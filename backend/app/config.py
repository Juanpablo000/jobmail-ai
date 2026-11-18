from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Base de datos (puerto 5433 para evitar conflicto con Postgres local en 5432)
    database_url: str = "postgresql+asyncpg://jobmail:jobmail@localhost:5433/jobmail_db"

    # Gmail API
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/callback"

    # LM Studio
    lm_studio_base_url: str = "http://localhost:1234/v1"
    lm_studio_chat_model: str = "ibm/granite-4-h-tiny"
    lm_studio_embed_model: str = "text-embedding-nomic-embed-text-v1.5"

    # Scheduler
    email_sync_interval_minutes: int = 30

    # App — como string separado por comas para facilitar el .env
    # Ej en .env: CORS_ORIGINS=http://localhost:5173,http://localhost:3000
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]


settings = Settings()
