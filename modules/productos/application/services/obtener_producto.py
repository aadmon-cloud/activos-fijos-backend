from modules.productos.application.ports.producto_repository import ProductoRepositoryPort
from modules.productos.domain.entities.producto import Producto
from modules.productos.domain.errors import ProductoNoEncontradoError


class ObtenerProductoService:
    def __init__(self, producto_repository: ProductoRepositoryPort):
        self._producto_repository = producto_repository

    async def ejecutar(self, codigo: str) -> Producto:
        """Raises:
        ProductoNoEncontradoError: no existe un producto con ese código.
        """
        producto = await self._producto_repository.obtener_por_codigo(codigo)
        if producto is None:
            raise ProductoNoEncontradoError(codigo)
        return producto
