from modules.catalogos.application.ports.lugar_repository import LugarRepositoryPort
from modules.catalogos.application.ports.sede_repository import SedeRepositoryPort
from modules.catalogos.domain.errors import SedeEnUsoError, SedeNoEncontradaError


class EliminarSedeService:
    def __init__(self, sede_repository: SedeRepositoryPort, lugar_repository: LugarRepositoryPort):
        self._sede_repository = sede_repository
        self._lugar_repository = lugar_repository

    async def ejecutar(self, id_sede: str) -> None:
        sede = await self._sede_repository.obtener_por_id(id_sede)
        if sede is None:
            raise SedeNoEncontradaError(id_sede)

        if await self._lugar_repository.existe_alguno_con_sede(id_sede):
            raise SedeEnUsoError(id_sede)

        await self._sede_repository.eliminar(id_sede)
