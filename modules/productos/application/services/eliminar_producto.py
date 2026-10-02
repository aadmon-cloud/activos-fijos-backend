from modules.productos.application.ports.producto_repository import ProductoRepositoryPort
from modules.productos.domain.errors import ProductoNoEncontradoError


class EliminarProductoService:
    def __init__(self, producto_repository: ProductoRepositoryPort):
        self._producto_repository = producto_repository

    async def ejecutar(self, codigo: str) -> None:
        """Raises:
        ProductoNoEncontradoError: no existe un producto con ese código.
        """
        eliminado = await self._producto_repository.eliminar(codigo)
        if not eliminado:
            raise ProductoNoEncontradoError(codigo)
