import logging

from shared.application.notifications.ports import NotificadorPort

logger = logging.getLogger(__name__)


class LogNotificador(NotificadorPort):
    """Adaptador provisional: registra la notificacion en el log en vez de enviar un correo real.

    Se reemplaza por un adaptador Gmail/SMTP cuando el sistema de notificaciones real se
    construya, sin tocar los modulos que ya dependen de NotificadorPort.
    """

    async def notificar(self, destinatarios: list[str], asunto: str, cuerpo: str) -> None:
        logger.info("Notificacion (stub) para %s | asunto=%s | cuerpo=%s", destinatarios, asunto, cuerpo)
