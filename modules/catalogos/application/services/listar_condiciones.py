from modules.catalogos.application.dto.condicion_dto import CondicionDTO, condicion_a_dto
from modules.catalogos.application.ports.condicion_repository import CondicionRepositoryPort


class ListarCondicionesService:
    def __init__(self, condicion_repository: CondicionRepositoryPort):
        self._condicion_repository = condicion_repository

    async def ejecutar(self) -> list[CondicionDTO]:
        condiciones = await self._condicion_repository.listar()
        return [condicion_a_dto(condicion) for condicion in condiciones]
