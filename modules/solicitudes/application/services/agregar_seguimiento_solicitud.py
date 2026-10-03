from dataclasses import replace
from datetime import UTC, datetime

from modules.solicitudes.application.dto.agregar_seguimiento_solicitud_dto import (
    AgregarSeguimientoSolicitudDTO,
)
from modules.solicitudes.application.dto.solicitud_dto import SolicitudDTO, solicitud_a_dto
from modules.solicitudes.application.ports.solicitud_repository import SolicitudRepositoryPort
from modules.solicitudes.domain.entities import EntradaSeguimiento
from modules.solicitudes.domain.errors import SolicitudNoEncontradaError, SolicitudSinPermisoError
from modules.solicitudes.domain.permisos import puede_gestionar
from shared.domain.entities.audit import AuditPersona


class AgregarSeguimientoSolicitudService:
    def __init__(self, solicitud_repository: SolicitudRepositoryPort):
        self._solicitud_repository = solicitud_repository

    async def ejecutar(self, dto: AgregarSeguimientoSolicitudDTO) -> SolicitudDTO:
        solicitud = await self._solicitud_repository.obtener_por_id(dto.id_solicitud)
        if solicitud is None:
            raise SolicitudNoEncontradaError(dto.id_solicitud)

        if not puede_gestionar(solicitud, dto.actor_id, dto.actor_rol, dto.actor_area_id):
            raise SolicitudSinPermisoError(dto.id_solicitud)

        nueva_entrada = EntradaSeguimiento(
            autor=AuditPersona(
                id_persona=dto.actor_id, nombre=dto.actor_nombre, fecha=datetime.now(UTC)
            ),
            comentario=dto.comentario.strip(),
            estado_anterior=None,
            estado_nuevo=None,
        )

        solicitud_actualizada = replace(
            solicitud, seguimiento=[*solicitud.seguimiento, nueva_entrada]
        )

        solicitud_guardada = await self._solicitud_repository.guardar(solicitud_actualizada)
        return solicitud_a_dto(solicitud_guardada)
