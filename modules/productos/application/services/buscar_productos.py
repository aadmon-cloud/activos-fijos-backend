from modules.productos.application.ports.producto_repository import ProductoRepositoryPort
from modules.productos.domain.entities.producto import Producto


class BuscarProductosService:
    def __init__(self, producto_repository: ProductoRepositoryPort):
        self._producto_repository = producto_repository

    async def ejecutar(self, texto: str) -> list[Producto]:
        return await self._producto_repository.buscar_por_texto(texto)
