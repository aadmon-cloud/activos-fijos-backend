from modules.activos.application.dto.activo_dto import ActivoDTO, activo_a_dto
from modules.activos.application.dto.listar_activos_dto import ListarActivosDTO
from modules.activos.application.ports.activo_repository import ActivoRepositoryPort

_LIMITE_MAXIMO = 1000


class ListarActivosService:
    def __init__(self, activo_repository: ActivoRepositoryPort):
        self._activo_repository = activo_repository

    async def ejecutar(self, dto: ListarActivosDTO) -> list[ActivoDTO]:
        limit = min(dto.limit, _LIMITE_MAXIMO)
        activos = await self._activo_repository.listar(
            area_id=dto.area_id,
            categoria_id=dto.categoria_id,
            responsable_id=dto.responsable_id,
            condicion_id=dto.condicion_id,
            sede_id=dto.sede_id,
            lugar_id=dto.lugar_id,
            estado_ciclo_vida=dto.estado_ciclo_vida,
            busqueda=dto.busqueda,
            skip=dto.skip,
            limit=limit,
        )
        return [activo_a_dto(activo) for activo in activos]
