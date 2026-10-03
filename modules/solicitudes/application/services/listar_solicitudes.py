from modules.solicitudes.application.dto.listar_solicitudes_dto import ListarSolicitudesDTO
from modules.solicitudes.application.dto.solicitud_dto import SolicitudDTO, solicitud_a_dto
from modules.solicitudes.application.ports.solicitud_repository import SolicitudRepositoryPort

_LIMITE_MAXIMO = 1000


class ListarSolicitudesService:
    def __init__(self, solicitud_repository: SolicitudRepositoryPort):
        self._solicitud_repository = solicitud_repository

    async def ejecutar(self, dto: ListarSolicitudesDTO) -> list[SolicitudDTO]:
        limit = min(dto.limit, _LIMITE_MAXIMO)
        solicitudes = await self._solicitud_repository.listar(
            tipo=dto.tipo,
            estado=dto.estado,
            activo_id=dto.activo_id,
            rol_asignado=dto.rol_asignado,
            area_id=dto.area_id,
            creado_por_id=dto.creado_por_id,
            skip=dto.skip,
            limit=limit,
        )
        return [solicitud_a_dto(solicitud) for solicitud in solicitudes]
