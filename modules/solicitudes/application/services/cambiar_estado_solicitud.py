from dataclasses import replace
from datetime import UTC, datetime

from modules.solicitudes.application.dto.cambiar_estado_solicitud_dto import (
    CambiarEstadoSolicitudDTO,
)
from modules.solicitudes.application.dto.solicitud_dto import SolicitudDTO, solicitud_a_dto
from modules.solicitudes.application.ports.solicitud_repository import SolicitudRepositoryPort
from modules.solicitudes.domain.entities import EntradaSeguimiento
from modules.solicitudes.domain.errors import (
    SolicitudNoEncontradaError,
    SolicitudSinPermisoError,
    TransicionEstadoSolicitudInvalidaError,
)
from modules.solicitudes.domain.permisos import puede_gestionar
from modules.solicitudes.domain.transiciones import es_transicion_valida
from shared.application.notifications.ports import NotificadorPort
from shared.domain.entities.audit import AuditPersona


class CambiarEstadoSolicitudService:
    def __init__(
        self,
        solicitud_repository: SolicitudRepositoryPort,
        notificador: NotificadorPort,
    ):
        self._solicitud_repository = solicitud_repository
        self._notificador = notificador

    async def ejecutar(self, dto: CambiarEstadoSolicitudDTO) -> SolicitudDTO:
        solicitud = await self._solicitud_repository.obtener_por_id(dto.id_solicitud)
        if solicitud is None:
            raise SolicitudNoEncontradaError(dto.id_solicitud)

        if not puede_gestionar(solicitud, dto.actor_id, dto.actor_rol, dto.actor_area_id):
            raise SolicitudSinPermisoError(dto.id_solicitud)

        if not es_transicion_valida(solicitud.estado, dto.estado_nuevo):
            raise TransicionEstadoSolicitudInvalidaError(
                solicitud.estado.value, dto.estado_nuevo.value
            )

        audit = AuditPersona(
            id_persona=dto.actor_id, nombre=dto.actor_nombre, fecha=datetime.now(UTC)
        )

        nueva_entrada = EntradaSeguimiento(
            autor=audit,
            comentario=dto.comentario or f"Estado cambiado a '{dto.estado_nuevo.value}'.",
            estado_anterior=solicitud.estado.value,
            estado_nuevo=dto.estado_nuevo.value,
        )

        solicitud_actualizada = replace(
            solicitud,
            estado=dto.estado_nuevo,
            seguimiento=[*solicitud.seguimiento, nueva_entrada],
            actualizado_por=audit,
        )

        solicitud_guardada = await self._solicitud_repository.guardar(solicitud_actualizada)

        await self._notificador.notificar(
            destinatarios=[f"usuario:{solicitud.creado_por.id_persona}"],
            asunto=f"Solicitud actualizada a '{dto.estado_nuevo.value}'",
            cuerpo=nueva_entrada.comentario,
        )

        return solicitud_a_dto(solicitud_guardada)
