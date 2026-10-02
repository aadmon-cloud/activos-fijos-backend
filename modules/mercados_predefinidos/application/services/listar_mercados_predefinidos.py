from modules.mercados_predefinidos.application.ports.mercado_predefinido_repository import (
    MercadoPredefinidoRepositoryPort,
)
from modules.mercados_predefinidos.domain.entities.mercado_predefinido import (
    MercadoPredefinido,
)


class ListarMercadosPredefinidosService:
    def __init__(self, mercado_repository: MercadoPredefinidoRepositoryPort):
        self._mercado_repository = mercado_repository

    async def ejecutar(self, solo_activos: bool = True) -> list[MercadoPredefinido]:
        return await self._mercado_repository.listar(solo_activos)
