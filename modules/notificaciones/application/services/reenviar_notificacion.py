from dataclasses import replace
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
from modules.notificaciones.domain.entities import EstadoNotificacion
from modules.notificaciones.domain.errors import (
    NotificacionNoEncontradaError,
    NotificacionNoReenviableError,
)
from shared.application.notifications.ports import NotificadorConAdjuntoPort


class ReenviarNotificacionService:
    """Vuelve a intentar una notificacion que fallo o se omitio. Los destinatarios se resuelven de nuevo,
    asi que un usuario que ya tiene correo, o uno que se desactivo, se tiene en cuenta."""

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

    async def ejecutar(self, id_notificacion: str) -> NotificacionDTO:
        notificacion = await self._notificacion_repository.obtener_por_id(id_notificacion)
        if notificacion is None:
            raise NotificacionNoEncontradaError(id_notificacion)

        if notificacion.estado == EstadoNotificacion.ENVIADA:
            raise NotificacionNoReenviableError(id_notificacion)

        estado, correos, detalle = await intentar_envio(
            notificacion.destinatarios,
            notificacion.asunto,
            notificacion.cuerpo,
            self._resolutor,
            self._configuracion,
            self._correo,
        )

        guardada = await self._notificacion_repository.guardar(
            replace(
                notificacion,
                correos=correos,
                estado=estado,
                detalle=detalle,
                intentos=notificacion.intentos + 1,
                actualizada_en=datetime.now(UTC),
            )
        )

        return notificacion_a_dto(guardada)
