from modules.activos.application.dto.entrada_historial_dto import (
    EntradaHistorialDTO,
    entrada_historial_a_dto,
)
from modules.activos.application.ports.activo_repository import ActivoRepositoryPort
from modules.activos.application.ports.historial_activo_repository import (
    HistorialActivoRepositoryPort,
)
from modules.activos.domain.errors import ActivoNoEncontradoError


class ObtenerHistorialActivoService:
    def __init__(
        self,
        activo_repository: ActivoRepositoryPort,
        historial_repository: HistorialActivoRepositoryPort,
    ):
        self._activo_repository = activo_repository
        self._historial_repository = historial_repository

    async def ejecutar(self, id_activo: str) -> list[EntradaHistorialDTO]:
        if await self._activo_repository.obtener_por_id(id_activo) is None:
            raise ActivoNoEncontradoError(id_activo)

        entradas = await self._historial_repository.listar_por_activo(id_activo)
        return [entrada_historial_a_dto(entrada) for entrada in entradas]
