from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    GCP_PROJECT_ID: str
    GOOGLE_CLOUD_RUN_AUDIENCE: str | None = None
    ENTORNO: str = "local"
    SYSTEM_NAME: str | None = None

    MONGO_URL: str
    MONGO_DB: str
    MONGO_CERT_SECRET_NAME: str | None = None

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 180

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
