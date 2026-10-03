from modules.catalogos.application.dto.lugar_dto import LugarDTO, lugar_a_dto
from modules.catalogos.application.ports.lugar_repository import LugarRepositoryPort
from modules.catalogos.domain.errors import LugarNoEncontradoError


class ObtenerLugarService:
    def __init__(self, lugar_repository: LugarRepositoryPort):
        self._lugar_repository = lugar_repository

    async def ejecutar(self, id_lugar: str) -> LugarDTO:
        lugar = await self._lugar_repository.obtener_por_id(id_lugar)
        if lugar is None:
            raise LugarNoEncontradoError(id_lugar)
        return lugar_a_dto(lugar)
