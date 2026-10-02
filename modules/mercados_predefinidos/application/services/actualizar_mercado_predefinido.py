from modules.mercados_predefinidos.application.dto.actualizar_mercado_predefinido import (
    ActualizarMercadoPredefinidoInput,
)
from modules.mercados_predefinidos.application.ports.mercado_predefinido_repository import (
    MercadoPredefinidoRepositoryPort,
)
from modules.mercados_predefinidos.domain.entities.mercado_predefinido import (
    MercadoPredefinido,
    ProductoKit,
)
from modules.mercados_predefinidos.domain.errors import MercadoNoEncontradoError
from modules.productos.application.ports.producto_repository import ProductoRepositoryPort
from modules.productos.domain.errors import ProductoNoEncontradoError
from shared.domain.entities.audit_persona import AuditPersona


class ActualizarMercadoPredefinidoService:
    def __init__(
        self,
        mercado_repository: MercadoPredefinidoRepositoryPort,
        producto_repository: ProductoRepositoryPort,
    ):
        self._mercado_repository = mercado_repository
        self._producto_repository = producto_repository

    async def ejecutar(
        self,
        nombre: str,
        entrada: ActualizarMercadoPredefinidoInput,
        actualizado_por: AuditPersona,
    ) -> MercadoPredefinido:
        """Raises:
        MercadoNoEncontradoError: no existe un mercado con ese nombre.
        ProductoNoEncontradoError: algún producto_id referenciado no existe.
        """
        mercado = await self._mercado_repository.obtener_por_nombre(nombre)
        if mercado is None:
            raise MercadoNoEncontradoError(nombre)

        productos = (
            await self._resolver_productos(entrada.productos)
            if entrada.productos is not None
            else None
        )

        mercado_actualizado = mercado.actualizar(
            actualizado_por=actualizado_por,
            descripcion=entrada.descripcion,
            productos=productos,
            activo=entrada.activo,
        )
        return await self._mercado_repository.actualizar(mercado_actualizado)

    async def _resolver_productos(self, items) -> list[ProductoKit]:
        productos = []
        for item in items:
            producto = await self._producto_repository.obtener_por_codigo(item.producto_id)
            if producto is None:
                raise ProductoNoEncontradoError(item.producto_id)
            productos.append(
                ProductoKit(
                    producto_id=item.producto_id,
                    cantidad=item.cantidad,
                    producto_nombre=producto.nombre,
                )
            )
        return productos
