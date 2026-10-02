from modules.movimientos.application.dto.registrar_entrada import RegistrarEntradaInput
from modules.movimientos.application.ports.movimiento_repository import MovimientoRepositoryPort
from modules.movimientos.application.services.ajustador_de_stock import AjustadorDeStockService
from modules.movimientos.domain.entities.movimiento import Movimiento
from shared.application.persistence.unit_of_work import UnitOfWorkFactory, UnitOfWorkPort
from shared.domain.entities.audit_persona import AuditPersona


class RegistrarEntradaService:
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
        entrada: RegistrarEntradaInput,
        creado_por: AuditPersona,
        uow: UnitOfWorkPort | None = None,
    ) -> Movimiento:
        """Registra una entrada individual: suma stock en la ubicación (crea la
        ubicación si no existía), recalcula `productos.stock_actual` como la
        suma de todas las ubicaciones, y crea el movimiento — todo en una sola
        transacción.

        Si se provee `uow`, participa de una transacción externa ya abierta
        (ej. `ConfirmarMovimientoPendienteService`) en vez de abrir la propia.

        Raises:
            ProductoNoEncontradoError: no existe un producto con ese código.
        """
        ubicacion_nombre = entrada.ubicacion or "ALMACEN_GENERAL"

        if uow is not None:
            return await self._registrar(entrada, ubicacion_nombre, creado_por, uow)
        async with self._unit_of_work_factory() as uow:
            return await self._registrar(entrada, ubicacion_nombre, creado_por, uow)

    async def _registrar(self, entrada, ubicacion_nombre, creado_por, uow) -> Movimiento:
        producto = await self._ajustador_de_stock.incrementar(
            entrada.producto_codigo, ubicacion_nombre, entrada.cantidad, creado_por, uow
        )

        movimiento = Movimiento.registrar_entrada(
            producto_codigo=entrada.producto_codigo,
            producto_nombre=producto.nombre,
            cantidad=entrada.cantidad,
            motivo=entrada.motivo,
            tipo_origen=entrada.tipo_origen,
            origen_nombre=entrada.origen_nombre,
            ubicacion=ubicacion_nombre,
            notas=entrada.notas,
            creado_por=creado_por,
        )
        return await self._movimiento_repository.crear(movimiento, uow=uow)
