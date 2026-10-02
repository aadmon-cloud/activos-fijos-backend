from modules.productos.application.dto.actualizar_producto import ActualizarProductoInput
from modules.productos.application.ports.producto_repository import ProductoRepositoryPort
from modules.productos.domain.entities.producto import Producto
from modules.productos.domain.errors import ProductoNoEncontradoError
from shared.domain.entities.audit_persona import AuditPersona


class ActualizarProductoService:
    def __init__(self, producto_repository: ProductoRepositoryPort):
        self._producto_repository = producto_repository

    async def ejecutar(
        self,
        codigo: str,
        entrada: ActualizarProductoInput,
        actualizado_por: AuditPersona,
    ) -> Producto:
        """Raises:
        ProductoNoEncontradoError: no existe un producto con ese código.
        """
        producto = await self._producto_repository.obtener_por_codigo(codigo)
        if producto is None:
            raise ProductoNoEncontradoError(codigo)

        producto_actualizado = producto.actualizar(
            actualizado_por=actualizado_por,
            nombre=entrada.nombre,
            descripcion=entrada.descripcion,
            categoria=entrada.categoria,
            stock_minimo=entrada.stock_minimo,
            precio_unitario=entrada.precio_unitario,
        )
        return await self._producto_repository.actualizar(producto_actualizado)
