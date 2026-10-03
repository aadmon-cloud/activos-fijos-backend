from modules.catalogos.application.dto.condicion_dto import CondicionDTO, condicion_a_dto
from modules.catalogos.application.ports.condicion_repository import CondicionRepositoryPort
from modules.catalogos.domain.errors import CondicionNoEncontradaError


class ObtenerCondicionService:
    def __init__(self, condicion_repository: CondicionRepositoryPort):
        self._condicion_repository = condicion_repository

    async def ejecutar(self, id_condicion: str) -> CondicionDTO:
        condicion = await self._condicion_repository.obtener_por_id(id_condicion)
        if condicion is None:
            raise CondicionNoEncontradaError(id_condicion)
        return condicion_a_dto(condicion)
