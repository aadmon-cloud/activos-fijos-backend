from modules.mercados_predefinidos.application.dto.crear_mercado_predefinido import (
    CrearMercadoPredefinidoInput,
)
from modules.mercados_predefinidos.application.ports.mercado_predefinido_repository import (
    MercadoPredefinidoRepositoryPort,
)
from modules.mercados_predefinidos.domain.entities.mercado_predefinido import (
    MercadoPredefinido,
    ProductoKit,
)
from modules.mercados_predefinidos.domain.errors import MercadoNombreDuplicadoError
from modules.productos.application.ports.producto_repository import ProductoRepositoryPort
from modules.productos.domain.errors import ProductoNoEncontradoError
from shared.domain.entities.audit_persona import AuditPersona


class CrearMercadoPredefinidoService:
    def __init__(
        self,
        mercado_repository: MercadoPredefinidoRepositoryPort,
        producto_repository: ProductoRepositoryPort,
    ):
        self._mercado_repository = mercado_repository
        self._producto_repository = producto_repository

    async def ejecutar(
        self, entrada: CrearMercadoPredefinidoInput, creado_por: AuditPersona
    ) -> MercadoPredefinido:
        """Raises:
        MercadoNombreDuplicadoError: ya existe un mercado con ese nombre.
        ProductoNoEncontradoError: algún producto_id referenciado no existe.
        """
        if await self._mercado_repository.existe_por_nombre(entrada.nombre):
            raise MercadoNombreDuplicadoError(entrada.nombre)

        productos = await self._resolver_productos(entrada.productos)

        nuevo_mercado = MercadoPredefinido.crear(
            nombre=entrada.nombre,
            descripcion=entrada.descripcion,
            productos=productos,
            creado_por=creado_por,
        )
        return await self._mercado_repository.crear(nuevo_mercado)

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
