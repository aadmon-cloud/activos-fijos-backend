from modules.movimientos.application.dto.registrar_entrada_multiple import (
    ItemEntradaMultipleInput,
    RegistrarEntradaMultipleInput,
)
from modules.movimientos.application.ports.movimiento_repository import MovimientoRepositoryPort
from modules.movimientos.application.services.ajustador_de_stock import AjustadorDeStockService
from modules.movimientos.domain.entities.movimiento import ItemMovimiento, Movimiento
from shared.application.persistence.unit_of_work import UnitOfWorkFactory, UnitOfWorkPort
from shared.domain.entities.audit_persona import AuditPersona


class RegistrarEntradaMultipleService:
    def __init__(
        self,
        movimiento_repository: MovimientoRepositoryPort,
        ajustador_de_stock: AjustadorDeStockService,
        unit_of_work_factory: UnitOfWorkFactory,
    ):
        self._movimiento_repository = movimiento_repository
        self._ajustador_de_stock = ajustador_de_stock
        self._unit_of_work_factory = unit_of_work_factory

    async def ejecutar(
        self,
        entrada: RegistrarEntradaMultipleInput,
        creado_por: AuditPersona,
        uow: UnitOfWorkPort | None = None,
    ) -> Movimiento:
        """Registra una sola entrada con varios productos, cada uno sumando
        stock en su propia ubicación (la del item, o la global del request,
        o "ALMACEN_GENERAL"). Recalcula `stock_actual` de cada producto
        afectado y crea un único `Movimiento` — todo en una transacción.

        Si se provee `uow`, participa de una transacción externa ya abierta
        (ej. `ConfirmarMovimientoPendienteService`) en vez de abrir la propia.

        Raises:
            ProductoNoEncontradoError: algún item referencia un producto inexistente.
        """
        if uow is not None:
            return await self._registrar(entrada, creado_por, uow)
        async with self._unit_of_work_factory() as uow:
            return await self._registrar(entrada, creado_por, uow)

    async def _registrar(
        self, entrada: RegistrarEntradaMultipleInput, creado_por: AuditPersona, uow
    ) -> Movimiento:
        items_movimiento = [
            await self._registrar_item(item, entrada.ubicacion, creado_por, uow)
            for item in entrada.productos
        ]

        movimiento = Movimiento.registrar_entrada_multiple(
            productos=items_movimiento,
            tipo_origen=entrada.tipo_origen,
            origen_nombre=entrada.origen_nombre,
            notas=entrada.notas,
            creado_por=creado_por,
        )
        return await self._movimiento_repository.crear(movimiento, uow=uow)

    async def _registrar_item(
        self,
        item: ItemEntradaMultipleInput,
        ubicacion_default: str | None,
        creado_por: AuditPersona,
        uow: UnitOfWorkPort,
    ) -> ItemMovimiento:
        ubicacion_final = item.ubicacion or ubicacion_default or "ALMACEN_GENERAL"

        producto = await self._ajustador_de_stock.incrementar(
            item.producto_codigo, ubicacion_final, item.cantidad, creado_por, uow
        )

        return ItemMovimiento(
            producto_codigo=item.producto_codigo,
            producto_nombre=producto.nombre,
            cantidad=item.cantidad,
            ubicacion=ubicacion_final,
        )
