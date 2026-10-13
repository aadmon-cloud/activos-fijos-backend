from modules.activos.application.dto.activo_con_nombres_dto import ListadoActivosDTO
from modules.activos.application.dto.listar_activos_dto import ListarActivosDTO
from modules.activos.application.ports.activo_repository import ActivoRepositoryPort
from modules.activos.application.ports.resolutor_nombres import ResolutorNombresPort
from modules.activos.application.services.enriquecimiento import con_nombres

_LIMITE_MAXIMO = 1000


class ListarActivosService:
    def __init__(
        self,
        activo_repository: ActivoRepositoryPort,
        resolutor_nombres: ResolutorNombresPort,
    ):
        self._activo_repository = activo_repository
        self._resolutor_nombres = resolutor_nombres

    async def ejecutar(self, dto: ListarActivosDTO) -> ListadoActivosDTO:
        limit = min(dto.limit, _LIMITE_MAXIMO)
        filtros = dict(
            area_id=dto.area_id,
            categoria_id=dto.categoria_id,
            responsable_id=dto.responsable_id,
            condicion_id=dto.condicion_id,
            sede_id=dto.sede_id,
            lugar_id=dto.lugar_id,
            estado_ciclo_vida=dto.estado_ciclo_vida,
            busqueda=dto.busqueda,
        )
        activos = await self._activo_repository.listar(**filtros, skip=dto.skip, limit=limit)
        total = await self._activo_repository.contar(**filtros)

        return ListadoActivosDTO(
            items=await con_nombres(activos, self._resolutor_nombres),
            total=total,
            skip=dto.skip,
            limit=limit,
        )
