from config.settings import settings
from modules.notificaciones.application.ports.configuracion_correo import ConfiguracionCorreoPort


class ConfiguracionCorreoSettings(ConfiguracionCorreoPort):
    """Hay correo configurado cuando estan el servidor, el usuario, el remitente y la contrasena (en el
    .env en local, o el nombre de su secreto en el resto de entornos)."""

    def esta_configurado(self) -> bool:
        tiene_clave = bool(
            settings.SMTP_PASSWORD
            if settings.ENTORNO == "local"
            else settings.SMTP_PASSWORD_SECRET_NAME
        )

        return bool(
            settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_FROM_EMAIL and tiene_clave
        )

    def url_aplicacion(self) -> str | None:
        return settings.APP_URL or None

    def remitente(self) -> str | None:
        return settings.SMTP_FROM_EMAIL or None
