from modules.movimientos.application.ports.generador_secuencial import GeneradorSecuencialPort
from modules.movimientos.application.ports.movimiento_repository import MovimientoRepositoryPort
from modules.movimientos.application.services.ajustador_de_stock import AjustadorDeStockService
from modules.movimientos.domain.entities.movimiento import ItemMovimiento, Movimiento
from modules.reservas.application.ports.reserva_repository import ReservaRepositoryPort
from modules.reservas.domain.entities.reserva import Reserva
from shared.application.persistence.unit_of_work import UnitOfWorkFactory, UnitOfWorkPort
from shared.domain.entities.audit_persona import AuditPersona

PREFIJO_REMISION = "RM"


class ConfirmarReservaKitService:
    """Estrategia "kit" de `ConfirmarReservaService` — recibe la `Reserva` ya
    resuelta y validada como modalidad kit por el dispatcher."""

    def __init__(
        self,
        reserva_repository: ReservaRepositoryPort,
        movimiento_repository: MovimientoRepositoryPort,
        ajustador_de_stock: AjustadorDeStockService,
        generador_secuencial: GeneradorSecuencialPort,
        unit_of_work_factory: UnitOfWorkFactory,
    ):
        self._reserva_repository = reserva_repository
        self._movimiento_repository = movimiento_repository
        self._ajustador_de_stock = ajustador_de_stock
        self._generador_secuencial = generador_secuencial
        self._unit_of_work_factory = unit_of_work_factory

    async def ejecutar(self, reserva: Reserva, confirmado_por: AuditPersona) -> Movimiento:
        """Confirma una reserva modalidad "kit" como una única salida (todos
        los items embebidos en `productos`), con una remisión propia.
        Descuenta stock por ubicación, recalcula `stock_actual` y borra la
        reserva — todo en una transacción.

        Raises:
            ProductoNoEncontradoError: algún item referencia un producto inexistente.
            MovimientoUbicacionNoEncontradaError: algún item referencia una ubicación inexistente.
            MovimientoStockInsuficienteError: stock físico insuficiente en alguna ubicación.
        """
        datos_adicionales = reserva.datos_adicionales or {}
        kit_nombre = datos_adicionales.get("kitNombre") or "Kit"
        cliente_destino = datos_adicionales.get("cliente") or None
        notas = datos_adicionales.get("notas") or None
        caso = datos_adicionales.get("caso") or None

        async with self._unit_of_work_factory() as uow:
            remision = await self._generador_secuencial.siguiente(
                nombre="remision", prefijo=PREFIJO_REMISION, uow=uow
            )

            items_movimiento = [
                await self._descontar_item(item, confirmado_por, uow) for item in reserva.items
            ]

            movimiento = Movimiento.registrar_kit(
                kit_nombre=kit_nombre,
                productos=items_movimiento,
                cliente_destino=cliente_destino,
                notas=notas,
                caso=caso,
                remision=remision,
                creado_por=confirmado_por,
            )
            movimiento_creado = await self._movimiento_repository.crear(movimiento, uow=uow)

            await self._reserva_repository.eliminar(reserva.session_id, uow=uow)

        return movimiento_creado

    async def _descontar_item(
        self, item, creado_por: AuditPersona, uow: UnitOfWorkPort
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
