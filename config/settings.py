from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    GCP_PROJECT_ID: str
    GOOGLE_CLOUD_RUN_AUDIENCE: str | None = None

    # ID de cliente OAuth de Google (publico, no es un secreto) con el que se valida el ingreso de los usuarios.
    GOOGLE_CLIENT_ID: str | None = None

    # El ingreso es solo con Google. Esta opcion reabre el ingreso con contrasena y existe unicamente para las
    # pruebas automatizadas en local: en produccion debe quedar en false.
    LOGIN_PASSWORD_HABILITADO: bool = False
    ENTORNO: str = "local"
    SYSTEM_NAME: str | None = None

    MONGO_URL: str
    MONGO_DB: str
    MONGO_CERT_SECRET_NAME: str | None = None

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 180

    COOKIE_NAME: str = "access_token"
    COOKIE_SECURE: bool = True
    COOKIE_SAMESITE: Literal["strict", "lax", "none"] = "strict"
    COOKIE_DOMAIN: str | None = None

    CORS_ORIGINS: list[str] = []

    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_PASSWORD_SECRET_NAME: str | None = None
    SMTP_FROM_EMAIL: str | None = None
    SMTP_FROM_NAME: str = "Sistema de Activos Fijos"
    SMTP_USE_TLS: bool = True

    # Direccion publica del frontend, para los enlaces de los correos (sin barra final). Sin ella los
    # correos no llevan enlace.
    APP_URL: str | None = None

    # Cuenta de servicio de Cloud Scheduler autorizada a disparar los recordatorios con su token de
    # identidad. Sin ella solo el administrador puede dispararlos.
    SCHEDULER_SERVICE_ACCOUNT_EMAIL: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
