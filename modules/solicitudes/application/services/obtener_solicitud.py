from modules.solicitudes.application.dto.solicitud_dto import SolicitudDTO, solicitud_a_dto
from modules.solicitudes.application.ports.solicitud_repository import SolicitudRepositoryPort
from modules.solicitudes.domain.errors import SolicitudNoEncontradaError


class ObtenerSolicitudService:
    def __init__(self, solicitud_repository: SolicitudRepositoryPort):
        self._solicitud_repository = solicitud_repository

    async def ejecutar(self, id_solicitud: str) -> SolicitudDTO:
        solicitud = await self._solicitud_repository.obtener_por_id(id_solicitud)
        if solicitud is None:
            raise SolicitudNoEncontradaError(id_solicitud)
        return solicitud_a_dto(solicitud)
