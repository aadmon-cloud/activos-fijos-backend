from modules.catalogos.application.ports.condicion_repository import CondicionRepositoryPort
from modules.catalogos.application.ports.verificador_uso_en_activos import (
    VerificadorUsoEnActivosPort,
)
from modules.catalogos.domain.errors import CondicionEnUsoError, CondicionNoEncontradaError


class EliminarCondicionService:
    def __init__(
        self,
        condicion_repository: CondicionRepositoryPort,
        verificador_uso: VerificadorUsoEnActivosPort,
    ):
        self._condicion_repository = condicion_repository
        self._verificador_uso = verificador_uso

    async def ejecutar(self, id_condicion: str) -> None:
        condicion = await self._condicion_repository.obtener_por_id(id_condicion)
        if condicion is None:
            raise CondicionNoEncontradaError(id_condicion)

        if await self._verificador_uso.condicion_esta_en_uso(id_condicion):
            raise CondicionEnUsoError(id_condicion)

        await self._condicion_repository.eliminar(id_condicion)
