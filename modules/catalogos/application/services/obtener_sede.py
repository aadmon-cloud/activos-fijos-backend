from modules.catalogos.application.dto.sede_dto import SedeDTO, sede_a_dto
from modules.catalogos.application.ports.sede_repository import SedeRepositoryPort
from modules.catalogos.domain.errors import SedeNoEncontradaError


class ObtenerSedeService:
    def __init__(self, sede_repository: SedeRepositoryPort):
        self._sede_repository = sede_repository

    async def ejecutar(self, id_sede: str) -> SedeDTO:
        sede = await self._sede_repository.obtener_por_id(id_sede)
        if sede is None:
            raise SedeNoEncontradaError(id_sede)
        return sede_a_dto(sede)
