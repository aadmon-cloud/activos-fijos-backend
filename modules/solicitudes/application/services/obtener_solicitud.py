from dataclasses import replace

from modules.solicitudes.application.dto.obtener_solicitud_dto import ObtenerSolicitudDTO
from modules.solicitudes.application.dto.solicitud_dto import SolicitudConNombresDTO
from modules.solicitudes.application.ports.resolutor_referencias import ResolutorReferenciasPort
from modules.solicitudes.application.ports.solicitud_repository import SolicitudRepositoryPort
from modules.solicitudes.application.services.enriquecimiento import con_nombres
from modules.solicitudes.domain.errors import SolicitudNoEncontradaError
from modules.solicitudes.domain.permisos import (
    estados_destino_permitidos,
    puede_comentar,
    puede_ver,
)


class ObtenerSolicitudService:
    def __init__(
        self,
        solicitud_repository: SolicitudRepositoryPort,
        resolutor_referencias: ResolutorReferenciasPort,
    ):
        self._solicitud_repository = solicitud_repository
        self._resolutor_referencias = resolutor_referencias

    async def ejecutar(self, dto: ObtenerSolicitudDTO) -> SolicitudConNombresDTO:
        solicitud = await self._solicitud_repository.obtener_por_id(dto.id_solicitud)

        # Una solicitud que el usuario no puede ver responde igual que una inexistente:
        # no se revela que existe.
        if solicitud is None or not puede_ver(
            solicitud, dto.actor_id, dto.actor_rol, dto.actor_area_id
        ):
            raise SolicitudNoEncontradaError(dto.id_solicitud)

        detalle = (await con_nombres([solicitud], self._resolutor_referencias))[0]

        return replace(
            detalle,
            estados_permitidos=[
                estado.value
                for estado in estados_destino_permitidos(
                    solicitud, dto.actor_id, dto.actor_rol, dto.actor_area_id
                )
            ],
            puede_comentar=puede_comentar(
                solicitud, dto.actor_id, dto.actor_rol, dto.actor_area_id
            ),
        )
