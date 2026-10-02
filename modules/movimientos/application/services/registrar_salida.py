from modules.movimientos.application.dto.registrar_salida import RegistrarSalidaInput
from modules.movimientos.application.ports.generador_secuencial import GeneradorSecuencialPort
from modules.movimientos.application.ports.movimiento_repository import MovimientoRepositoryPort
from modules.movimientos.application.services.ajustador_de_stock import AjustadorDeStockService
from modules.movimientos.domain.entities.movimiento import Movimiento
from shared.application.persistence.unit_of_work import UnitOfWorkFactory, UnitOfWorkPort
from shared.domain.entities.audit_persona import AuditPersona

PREFIJO_REMISION = "RM"


class RegistrarSalidaService:
    def __init__(
        self,
        movimiento_repository: MovimientoRepositoryPort,
        ajustador_de_stock: AjustadorDeStockService,
        generador_secuencial: GeneradorSecuencialPort,
        unit_of_work_factory: UnitOfWorkFactory,
    ):
        self._movimiento_repository = movimiento_repository
        self._ajustador_de_stock = ajustador_de_stock
        self._generador_secuencial = generador_secuencial
        self._unit_of_work_factory = unit_of_work_factory

    async def ejecutar(
        self,
        entrada: RegistrarSalidaInput,
        creado_por: AuditPersona,
        uow: UnitOfWorkPort | None = None,
    ) -> Movimiento:
        """Registra una salida individual: valida stock físico en la ubicación
        indicada (única fuente de verdad, no se revalida contra el total
        denormalizado de `productos`), genera la remisión y descuenta stock —
        todo en una sola transacción.

        Si se provee `uow`, participa de una transacción externa ya abierta
        (ej. `ConfirmarMovimientoPendienteService`) en vez de abrir la propia.

        Raises:
            ProductoNoEncontradoError: no existe un producto con ese código.
            MovimientoUbicacionNoEncontradaError: el producto no tiene esa ubicación.
            MovimientoStockInsuficienteError: no hay stock físico suficiente ahí.
        """
        if uow is not None:
            return await self._registrar(entrada, creado_por, uow)
        async with self._unit_of_work_factory() as uow:
            return await self._registrar(entrada, creado_por, uow)

    async def _registrar(self, entrada, creado_por, uow) -> Movimiento:
        remision = await self._generador_secuencial.siguiente(
            nombre="remision", prefijo=PREFIJO_REMISION, uow=uow
        )

        producto = await self._ajustador_de_stock.descontar(
            entrada.producto_codigo, entrada.ubicacion, entrada.cantidad, creado_por, uow
        )

        movimiento = Movimiento.registrar_salida(
            producto_codigo=entrada.producto_codigo,
            producto_nombre=producto.nombre,
            cantidad=entrada.cantidad,
            motivo=entrada.motivo,
            cliente_destino=entrada.cliente_destino,
            ubicacion=entrada.ubicacion,
            notas=entrada.notas,
            remision=remision,
            creado_por=creado_por,
        )
        return await self._movimiento_repository.crear(movimiento, uow=uow)
