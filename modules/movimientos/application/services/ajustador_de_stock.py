from modules.movimientos.domain.errors import (
    MovimientoStockInsuficienteError,
    MovimientoUbicacionNoEncontradaError,
)
from modules.productos.application.ports.producto_repository import ProductoRepositoryPort
from modules.productos.domain.entities.producto import Producto
from modules.productos.domain.errors import ProductoNoEncontradoError
from modules.ubicaciones.application.ports.ubicacion_repository import UbicacionRepositoryPort
from modules.ubicaciones.domain.entities.ubicacion import Ubicacion
from shared.application.persistence.unit_of_work import UnitOfWorkPort
from shared.domain.entities.audit_persona import AuditPersona


class AjustadorDeStockService:
    """Capacidad compartida por los servicios de `movimientos` que mutan
    stock: descontar (salidas, confirmaciones de reserva) o incrementar
    (entradas). Centraliza la secuencia obtener producto/ubicación → validar
    → mutar `stock_fisico` → recalcular `stock_actual` del producto como la
    suma de todas sus ubicaciones → persistir ambos, dentro de una `uow` ya
    abierta por el caller."""

    def __init__(
        self,
        producto_repository: ProductoRepositoryPort,
        ubicacion_repository: UbicacionRepositoryPort,
    ):
        self._producto_repository = producto_repository
        self._ubicacion_repository = ubicacion_repository

    async def descontar(
        self,
        producto_codigo: str,
        ubicacion: str,
        cantidad: int,
        creado_por: AuditPersona,
        uow: UnitOfWorkPort,
    ) -> Producto:
        """Descuenta `cantidad` del stock físico de una ubicación existente y
        recalcula el stock total del producto.

        Raises:
            ProductoNoEncontradoError: no existe un producto con ese código.
            MovimientoUbicacionNoEncontradaError: el producto no tiene esa ubicación.
            MovimientoStockInsuficienteError: no hay stock físico suficiente ahí.
        """
        producto = await self._producto_repository.obtener_por_codigo(producto_codigo)
        if producto is None:
            raise ProductoNoEncontradoError(producto_codigo)

        ubicacion_actual = await self._ubicacion_repository.obtener(producto_codigo, ubicacion)
        if ubicacion_actual is None:
            raise MovimientoUbicacionNoEncontradaError(producto_codigo, ubicacion)
        if ubicacion_actual.stock_fisico < cantidad:
            raise MovimientoStockInsuficienteError(
                producto_codigo,
                ubicacion,
                disponible=ubicacion_actual.stock_fisico,
                solicitado=cantidad,
            )

        nuevo_fisico = ubicacion_actual.stock_fisico - cantidad
        await self._ubicacion_repository.actualizar(
            ubicacion_actual.actualizar_stock_fisico(nuevo_fisico, creado_por), uow=uow
        )

        return await self._recalcular_stock_producto(producto, producto_codigo, uow)

    async def incrementar(
        self,
        producto_codigo: str,
        ubicacion: str,
        cantidad: int,
        creado_por: AuditPersona,
        uow: UnitOfWorkPort,
    ) -> Producto:
        """Suma `cantidad` al stock físico de una ubicación (la crea si no
        existía) y recalcula el stock total del producto.

        Raises:
            ProductoNoEncontradoError: no existe un producto con ese código.
        """
        producto = await self._producto_repository.obtener_por_codigo(producto_codigo)
        if producto is None:
            raise ProductoNoEncontradoError(producto_codigo)

        ubicacion_actual = await self._ubicacion_repository.obtener(producto_codigo, ubicacion)
        if ubicacion_actual is not None:
            nuevo_fisico = ubicacion_actual.stock_fisico + cantidad
            await self._ubicacion_repository.actualizar(
                ubicacion_actual.actualizar_stock_fisico(nuevo_fisico, creado_por), uow=uow
            )
        else:
            nueva_ubicacion = Ubicacion.crear(
                producto_codigo=producto_codigo,
                ubicacion=ubicacion,
                stock_fisico=cantidad,
                creado_por=creado_por,
            )
            await self._ubicacion_repository.crear(nueva_ubicacion, uow=uow)

        return await self._recalcular_stock_producto(producto, producto_codigo, uow)

    async def _recalcular_stock_producto(
        self, producto: Producto, producto_codigo: str, uow: UnitOfWorkPort
    ) -> Producto:
        todas = await self._ubicacion_repository.listar_por_producto(producto_codigo, uow=uow)
        nuevo_total = sum(u.stock_fisico for u in todas)
        return await self._producto_repository.actualizar(
            producto.recalcular_stock(nuevo_total), uow=uow
        )
