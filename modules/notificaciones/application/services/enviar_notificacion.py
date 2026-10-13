from datetime import UTC, datetime

from modules.notificaciones.application.dto.notificacion_dto import NotificacionDTO, notificacion_a_dto
from modules.notificaciones.application.ports.configuracion_correo import ConfiguracionCorreoPort
from modules.notificaciones.application.ports.notificacion_repository import (
    NotificacionRepositoryPort,
)
from modules.notificaciones.application.ports.resolutor_destinatarios import (
    ResolutorDestinatariosPort,
)
from modules.notificaciones.application.services.envio import intentar_envio
from modules.notificaciones.domain.entities import Notificacion
from modules.notificaciones.domain.limites import limpiar_asunto, limpiar_cuerpo
from shared.application.notifications.enlaces import resolver_enlaces
from shared.application.notifications.ports import NotificadorConAdjuntoPort


class EnviarNotificacionService:
    """Envia un aviso por correo y deja constancia de lo que paso (enviado, fallido u omitido)."""

    def __init__(
        self,
        notificacion_repository: NotificacionRepositoryPort,
        resolutor: ResolutorDestinatariosPort,
        configuracion: ConfiguracionCorreoPort,
        correo: NotificadorConAdjuntoPort,
    ):
        self._notificacion_repository = notificacion_repository
        self._resolutor = resolutor
        self._configuracion = configuracion
        self._correo = correo

    async def ejecutar(self, destinatarios: list[str], asunto: str, cuerpo: str) -> NotificacionDTO:
        asunto_limpio = limpiar_asunto(asunto)
        cuerpo_limpio = limpiar_cuerpo(resolver_enlaces(cuerpo, self._configuracion.url_aplicacion()))

        estado, correos, detalle = await intentar_envio(
            destinatarios,
            asunto_limpio,
            cuerpo_limpio,
            self._resolutor,
            self._configuracion,
            self._correo,
        )
        ahora = datetime.now(UTC)

        guardada = await self._notificacion_repository.guardar(
            Notificacion(
                id=None,
                destinatarios=destinatarios,
                correos=correos,
                asunto=asunto_limpio,
                cuerpo=cuerpo_limpio,
                estado=estado,
                detalle=detalle,
                intentos=1,
                creada_en=ahora,
                actualizada_en=ahora,
            )
        )

        return notificacion_a_dto(guardada)
