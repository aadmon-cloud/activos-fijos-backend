from modules.catalogos.application.ports.area_repository import AreaRepositoryPort
from modules.catalogos.application.ports.verificador_uso_en_activos import (
    VerificadorUsoEnActivosPort,
)
from modules.catalogos.domain.errors import AreaEnUsoError, AreaNoEncontradaError


class EliminarAreaService:
    def __init__(
        self,
        area_repository: AreaRepositoryPort,
        verificador_uso: VerificadorUsoEnActivosPort,
    ):
        self._area_repository = area_repository
        self._verificador_uso = verificador_uso

    async def ejecutar(self, id_area: str) -> None:
        area = await self._area_repository.obtener_por_id(id_area)
        if area is None:
            raise AreaNoEncontradaError(id_area)

        if await self._verificador_uso.area_esta_en_uso(id_area):
            raise AreaEnUsoError(id_area)

        await self._area_repository.eliminar(id_area)
