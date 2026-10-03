from modules.catalogos.application.dto.area_dto import AreaDTO, area_a_dto
from modules.catalogos.application.ports.area_repository import AreaRepositoryPort
from modules.catalogos.domain.errors import AreaNoEncontradaError


class ObtenerAreaService:
    def __init__(self, area_repository: AreaRepositoryPort):
        self._area_repository = area_repository

    async def ejecutar(self, id_area: str) -> AreaDTO:
        area = await self._area_repository.obtener_por_id(id_area)
        if area is None:
            raise AreaNoEncontradaError(id_area)
        return area_a_dto(area)
