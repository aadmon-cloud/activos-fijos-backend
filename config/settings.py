from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    MONGO_URL: str
    MONGO_DB: str

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480

    # Usado por incrementos futuros de auth: link del email de recuperacion
    # de password y redireccion final del callback de Google OAuth.
    FRONTEND_URL: str = "http://localhost:3000"

    # SMTP para el email de recuperacion de password. Si SMTP_USER/SMTP_PASSWORD
    # quedan vacios, SmtpEmailSender no envia nada y retorna False (no falla el flujo).
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    FROM_EMAIL: str = ""

    # Google OAuth. Vacias por defecto: la app arranca igual, solo falla
    # (GoogleOAuthNoConfiguradoError) si se usa /api/auth/google sin configurar esto.
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = ""

    # Almacenamiento de archivos en disco (StorageRepositoryPort de `movimientos`,
    # ej. PDFs firmados). Ruta relativa a la raiz del proyecto.
    STORAGE_DIR: str = "storage"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
