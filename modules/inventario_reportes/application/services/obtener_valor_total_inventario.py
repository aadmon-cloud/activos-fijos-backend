from modules.productos.application.ports.producto_repository import ProductoRepositoryPort


class ObtenerValorTotalInventarioService:
    def __init__(self, producto_repository: ProductoRepositoryPort):
        self._producto_repository = producto_repository

    async def ejecutar(self) -> float:
        return await self._producto_repository.calcular_valor_total()
