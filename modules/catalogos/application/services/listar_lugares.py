from modules.catalogos.application.dto.listar_lugares_dto import ListarLugaresDTO
from modules.catalogos.application.dto.lugar_dto import LugarDTO, lugar_a_dto
from modules.catalogos.application.ports.lugar_repository import LugarRepositoryPort


class ListarLugaresService:
    def __init__(self, lugar_repository: LugarRepositoryPort):
        self._lugar_repository = lugar_repository

    async def ejecutar(self, dto: ListarLugaresDTO) -> list[LugarDTO]:
        lugares = await self._lugar_repository.listar(sede_id=dto.sede_id)
        return [lugar_a_dto(lugar) for lugar in lugares]
