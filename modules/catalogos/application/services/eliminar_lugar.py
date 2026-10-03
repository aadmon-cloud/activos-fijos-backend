from modules.catalogos.application.ports.lugar_repository import LugarRepositoryPort
from modules.catalogos.application.ports.verificador_uso_en_activos import (
    VerificadorUsoEnActivosPort,
)
from modules.catalogos.domain.errors import LugarEnUsoError, LugarNoEncontradoError


class EliminarLugarService:
    def __init__(
        self,
        lugar_repository: LugarRepositoryPort,
        verificador_uso: VerificadorUsoEnActivosPort,
    ):
        self._lugar_repository = lugar_repository
        self._verificador_uso = verificador_uso

    async def ejecutar(self, id_lugar: str) -> None:
        lugar = await self._lugar_repository.obtener_por_id(id_lugar)
        if lugar is None:
            raise LugarNoEncontradoError(id_lugar)

        if await self._verificador_uso.lugar_esta_en_uso(id_lugar):
            raise LugarEnUsoError(id_lugar)

        await self._lugar_repository.eliminar(id_lugar)
