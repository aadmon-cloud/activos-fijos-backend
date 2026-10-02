import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from modules.auth.application.ports.email_sender import EmailSenderPort

logger = logging.getLogger(__name__)


class SmtpEmailSender(EmailSenderPort):
    def __init__(
        self,
        smtp_server: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        from_email: str,
        frontend_url: str,
    ):
        self._smtp_server = smtp_server
        self._smtp_port = smtp_port
        self._smtp_user = smtp_user
        self._smtp_password = smtp_password
        self._from_email = from_email or smtp_user
        self._frontend_url = frontend_url

    def enviar_recuperacion_password(self, email: str, token: str) -> bool:
        if not self._smtp_user or not self._smtp_password:
            logger.warning("Email no configurado (SMTP_USER/SMTP_PASSWORD vacios).")
            return False

        enlace = f"{self._frontend_url}/reset-password?token={token}"
        asunto = "Recuperación de contraseña"
        cuerpo_texto = (
            "Has solicitado restablecer tu contraseña.\n\n"
            f"Enlace (válido por 1 hora): {enlace}\n\n"
            "Si no solicitaste este cambio, ignora este mensaje."
        )
        cuerpo_html = (
            "<html><body>"
            "<p>Has solicitado restablecer tu contraseña.</p>"
            f'<p><a href="{enlace}">Restablecer contraseña</a> (válido por 1 hora).</p>'
            "<p>Si no solicitaste este cambio, ignora este mensaje.</p>"
            "</body></html>"
        )

        try:
            mensaje = MIMEMultipart("alternative")
            mensaje["Subject"] = asunto
            mensaje["From"] = self._from_email
            mensaje["To"] = email
            mensaje.attach(MIMEText(cuerpo_texto, "plain"))
            mensaje.attach(MIMEText(cuerpo_html, "html"))

            with smtplib.SMTP(self._smtp_server, self._smtp_port) as servidor:
                servidor.starttls()
                servidor.login(self._smtp_user, self._smtp_password)
                servidor.send_message(mensaje)

            return True
        except Exception:
            logger.exception("Error enviando email de recuperación a %s", email)
            return False
