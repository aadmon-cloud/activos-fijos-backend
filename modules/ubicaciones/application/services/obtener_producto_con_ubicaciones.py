from modules.productos.application.ports.producto_repository import ProductoRepositoryPort
from modules.productos.domain.entities.producto import Producto
from modules.productos.domain.errors import ProductoNoEncontradoError
from modules.ubicaciones.application.ports.ubicacion_repository import UbicacionRepositoryPort
from modules.ubicaciones.domain.entities.ubicacion import Ubicacion


class ObtenerProductoConUbicacionesService:
    def __init__(
        self,
        ubicacion_repository: UbicacionRepositoryPort,
        producto_repository: ProductoRepositoryPort,
    ):
        self._ubicacion_repository = ubicacion_repository
        self._producto_repository = producto_repository

    async def ejecutar(self, producto_codigo: str) -> tuple[Producto, list[Ubicacion]]:
        """Raises:
        ProductoNoEncontradoError: no existe un producto con ese código.
        """
        producto = await self._producto_repository.obtener_por_codigo(producto_codigo)
        if producto is None:
            raise ProductoNoEncontradoError(producto_codigo)

        ubicaciones = await self._ubicacion_repository.listar_por_producto(producto_codigo)
        return producto, ubicaciones
