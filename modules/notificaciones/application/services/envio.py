import logging

from modules.notificaciones.application.ports.configuracion_correo import ConfiguracionCorreoPort
from modules.notificaciones.application.ports.resolutor_destinatarios import (
    ResolutorDestinatariosPort,
)
from modules.notificaciones.domain.entities import EstadoNotificacion
from modules.notificaciones.domain.limites import DESTINATARIOS_MAXIMO, acotar_detalle
from shared.application.notifications.ports import NotificadorConAdjuntoPort

logger = logging.getLogger(__name__)

DETALLE_SIN_DESTINATARIOS = "Ningun destinatario activo tiene correo."
DETALLE_CORREO_NO_CONFIGURADO = "El correo no esta configurado."


async def intentar_envio(
    destinatarios: list[str],
    asunto: str,
    cuerpo: str,
    resolutor: ResolutorDestinatariosPort,
    configuracion: ConfiguracionCorreoPort,
    correo: NotificadorConAdjuntoPort,
) -> tuple[EstadoNotificacion, list[str], str | None]:
    """Resuelve los correos y envia. Nunca lanza: un fallo se devuelve como estado FALLIDA con su detalle
    (acotado), para que avisar jamas rompa lo que el usuario estaba haciendo."""
    correos: list[str] = []

    try:
        correos = (await resolutor.resolver(destinatarios))[:DESTINATARIOS_MAXIMO]

        if not correos:
            return EstadoNotificacion.OMITIDA, correos, DETALLE_SIN_DESTINATARIOS

        if not configuracion.esta_configurado():
            return EstadoNotificacion.OMITIDA, correos, DETALLE_CORREO_NO_CONFIGURADO

        await correo.enviar(correos, asunto, cuerpo, [])

        return EstadoNotificacion.ENVIADA, correos, None
    except Exception as exc:
        logger.warning("No se pudo enviar la notificacion '%s': %s", asunto, exc)

        return EstadoNotificacion.FALLIDA, correos, acotar_detalle(f"{type(exc).__name__}: {exc}")
