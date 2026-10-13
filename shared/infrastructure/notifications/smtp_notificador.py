import asyncio
import smtplib
from email.message import EmailMessage

from config.settings import settings
from shared.application.notifications.ports import AdjuntoCorreo, NotificadorConAdjuntoPort
from shared.infrastructure.gcp.secret_manager import GestorSecretosGCP


# Los avisos se envian dentro de la peticion del usuario: si el servidor de correo no responde, no se le
# hace esperar medio minuto (el envio fallido queda registrado y se puede reintentar).
_TIMEOUT_SEGUNDOS = 15


class SMTPNotificador(NotificadorConAdjuntoPort):
    """Adaptador real de correo via SMTP generico (sirve para Gmail, Microsoft 365, etc.).

    La contrasena se lee del .env en local, o de GCP Secret Manager en el resto de entornos
    (mismo patron que el certificado de Mongo, ver shared/infrastructure/gcp/secret_manager.py).
    """

    def __init__(self):
        self._password_cacheada: str | None = None

    def _obtener_password(self) -> str:
        if settings.ENTORNO == "local" or not settings.SMTP_PASSWORD_SECRET_NAME:
            return settings.SMTP_PASSWORD or ""

        if self._password_cacheada is None:
            self._password_cacheada = GestorSecretosGCP(settings.GCP_PROJECT_ID).obtener_secreto(
                settings.SMTP_PASSWORD_SECRET_NAME
            )
        return self._password_cacheada

    async def enviar(
        self,
        destinatarios: list[str],
        asunto: str,
        cuerpo: str,
        adjuntos: list[AdjuntoCorreo],
    ) -> None:
        await asyncio.to_thread(self._enviar_sincrono, destinatarios, asunto, cuerpo, adjuntos)

    def _enviar_sincrono(
        self,
        destinatarios: list[str],
        asunto: str,
        cuerpo: str,
        adjuntos: list[AdjuntoCorreo],
    ) -> None:
        mensaje = EmailMessage()
        mensaje["Subject"] = asunto
        mensaje["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        mensaje["To"] = ", ".join(destinatarios)
        mensaje.set_content(cuerpo)

        for adjunto in adjuntos:
            tipo_principal, _, subtipo = adjunto.tipo_mime.partition("/")
            mensaje.add_attachment(
                adjunto.contenido,
                maintype=tipo_principal or "application",
                subtype=subtipo or "octet-stream",
                filename=adjunto.nombre,
            )

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=_TIMEOUT_SEGUNDOS) as servidor:
            if settings.SMTP_USE_TLS:
                servidor.starttls()
            servidor.login(settings.SMTP_USER, self._obtener_password())
            servidor.send_message(mensaje)
