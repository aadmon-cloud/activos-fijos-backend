from modules.catalogos.application.dto.area_dto import AreaDTO, area_a_dto
from modules.catalogos.application.ports.area_repository import AreaRepositoryPort


class ListarAreasService:
    def __init__(self, area_repository: AreaRepositoryPort):
        self._area_repository = area_repository

    async def ejecutar(self) -> list[AreaDTO]:
        areas = await self._area_repository.listar()
        return [area_a_dto(area) for area in areas]
