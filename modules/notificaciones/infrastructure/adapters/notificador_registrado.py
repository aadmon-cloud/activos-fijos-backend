import logging

from modules.notificaciones.application.services.enviar_notificacion import (
    EnviarNotificacionService,
)
from shared.application.notifications.ports import NotificadorPort

logger = logging.getLogger(__name__)


class NotificadorRegistrado(NotificadorPort):
    """El `NotificadorPort` que usan solicitudes, mantenimientos y movimientos: envia el aviso por correo
    y deja constancia. Avisar es secundario: si algo falla, se registra en el log y la accion del usuario
    sigue adelante."""

    def __init__(self, enviar_notificacion: EnviarNotificacionService):
        self._enviar_notificacion = enviar_notificacion

    async def notificar(self, destinatarios: list[str], asunto: str, cuerpo: str) -> None:
        try:
            await self._enviar_notificacion.ejecutar(destinatarios, asunto, cuerpo)
        except Exception:
            logger.exception("No se pudo registrar ni enviar la notificacion '%s'", asunto)
