from modules.movimientos.application.dto.registrar_salida_multiple import (
    ItemSalidaMultipleInput,
    RegistrarSalidaMultipleInput,
)
from modules.movimientos.application.ports.generador_secuencial import GeneradorSecuencialPort
from modules.movimientos.application.ports.movimiento_repository import MovimientoRepositoryPort
from modules.movimientos.application.services.ajustador_de_stock import AjustadorDeStockService
from modules.movimientos.domain.entities.movimiento import ItemMovimiento, Movimiento
from shared.application.persistence.unit_of_work import UnitOfWorkFactory, UnitOfWorkPort
from shared.domain.entities.audit_persona import AuditPersona

PREFIJO_REMISION = "RM"


class RegistrarSalidaMultipleService:
    """Registro directo de una salida con varios productos (sin pasar por
    `reservas`). El legacy (`crear_salida_multiple`) nunca tocaba
    `ubicaciones` ni generaba remisión — ambos corregidos acá, con el mismo
    patrón ya establecido por `ConfirmarReservaKitService`/`ConfirmarReservaMultipleService`."""

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
        entrada: RegistrarSalidaMultipleInput,
        creado_por: AuditPersona,
        uow: UnitOfWorkPort | None = None,
    ) -> Movimiento:
        """Si se provee `uow`, participa de una transacción externa ya abierta
        (ej. `ConfirmarMovimientoPendienteService`) en vez de abrir la propia.

        Raises:
        ProductoNoEncontradoError: algún item referencia un producto inexistente.
        MovimientoUbicacionNoEncontradaError: algún item referencia una ubicación inexistente.
        MovimientoStockInsuficienteError: stock físico insuficiente en alguna ubicación.
        """
        if uow is not None:
            return await self._registrar(entrada, creado_por, uow)
        async with self._unit_of_work_factory() as uow:
            return await self._registrar(entrada, creado_por, uow)

    async def _registrar(
        self, entrada: RegistrarSalidaMultipleInput, creado_por: AuditPersona, uow
    ) -> Movimiento:
        remision = await self._generador_secuencial.siguiente(
            nombre="remision", prefijo=PREFIJO_REMISION, uow=uow
        )

        items_movimiento = [
            await self._descontar_item(item, creado_por, uow) for item in entrada.productos
        ]

        movimiento = Movimiento.registrar_multiple(
            productos=items_movimiento,
            motivo=entrada.motivo,
            cliente_destino=entrada.cliente_destino,
            notas=entrada.notas,
            caso=None,
            remision=remision,
            creado_por=creado_por,
        )
        return await self._movimiento_repository.crear(movimiento, uow=uow)

    async def _descontar_item(
        self, item: ItemSalidaMultipleInput, creado_por: AuditPersona, uow: UnitOfWorkPort
    ) -> ItemMovimiento:
        producto = await self._ajustador_de_stock.descontar(
            item.producto_codigo, item.ubicacion, item.cantidad, creado_por, uow
        )
        return ItemMovimiento(
            producto_codigo=item.producto_codigo,
            producto_nombre=producto.nombre,
            cantidad=item.cantidad,
            ubicacion=item.ubicacion,
        )
