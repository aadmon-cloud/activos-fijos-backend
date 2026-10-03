from modules.activos.application.dto.activo_dto import ActivoDTO, activo_a_dto
from modules.activos.application.ports.activo_repository import ActivoRepositoryPort
from modules.activos.domain.errors import ActivoNoEncontradoError


class ObtenerActivoService:
    def __init__(self, activo_repository: ActivoRepositoryPort):
        self._activo_repository = activo_repository

    async def ejecutar(self, id_activo: str) -> ActivoDTO:
        activo = await self._activo_repository.obtener_por_id(id_activo)
        if activo is None:
            raise ActivoNoEncontradoError(id_activo)
        return activo_a_dto(activo)
