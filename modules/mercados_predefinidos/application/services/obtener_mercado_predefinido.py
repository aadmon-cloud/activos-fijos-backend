from modules.mercados_predefinidos.application.ports.mercado_predefinido_repository import (
    MercadoPredefinidoRepositoryPort,
)
from modules.mercados_predefinidos.domain.entities.mercado_predefinido import (
    MercadoPredefinido,
)
from modules.mercados_predefinidos.domain.errors import MercadoNoEncontradoError


class ObtenerMercadoPredefinidoService:
    def __init__(self, mercado_repository: MercadoPredefinidoRepositoryPort):
        self._mercado_repository = mercado_repository

    async def ejecutar(self, nombre: str) -> MercadoPredefinido:
        """Raises:
        MercadoNoEncontradoError: no existe un mercado con ese nombre.
        """
        mercado = await self._mercado_repository.obtener_por_nombre(nombre)
        if mercado is None:
            raise MercadoNoEncontradoError(nombre)
        return mercado
