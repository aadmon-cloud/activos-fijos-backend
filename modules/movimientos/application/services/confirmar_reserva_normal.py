from modules.movimientos.application.ports.generador_secuencial import GeneradorSecuencialPort
from modules.movimientos.application.ports.movimiento_repository import MovimientoRepositoryPort
from modules.movimientos.application.services.ajustador_de_stock import AjustadorDeStockService
from modules.movimientos.domain.entities.movimiento import Movimiento
from modules.reservas.application.ports.reserva_repository import ReservaRepositoryPort
from modules.reservas.domain.entities.reserva import ItemReserva, Reserva
from shared.application.persistence.unit_of_work import UnitOfWorkFactory, UnitOfWorkPort
from shared.domain.entities.audit_persona import AuditPersona

PREFIJO_REMISION = "RM"


class ConfirmarReservaNormalService:
    """Estrategia "normal" de `ConfirmarReservaService` — recibe la `Reserva`
    ya resuelta y validada como modalidad normal por el dispatcher; no vuelve
    a leerla ni a detectar la modalidad."""

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

    async def ejecutar(self, reserva: Reserva, confirmado_por: AuditPersona) -> list[Movimiento]:
        """Confirma una reserva modalidad "normal" como una o más salidas reales
        (una por item), compartiendo una sola remisión. Descuenta stock por
        ubicación una sola vez (corrige el doble descuento del legacy),
        recalcula `stock_actual` y borra la reserva — todo en una transacción.

        Raises:
            ProductoNoEncontradoError: algún item referencia un producto inexistente.
            MovimientoUbicacionNoEncontradaError: algún item referencia una ubicación inexistente.
            MovimientoStockInsuficienteError: stock físico insuficiente en alguna ubicación.
        """
        datos_adicionales = reserva.datos_adicionales or {}
        cliente_destino = datos_adicionales.get("cliente") or None
        notas = datos_adicionales.get("notas") or None

        async with self._unit_of_work_factory() as uow:
            remision = await self._generador_secuencial.siguiente(
                nombre="remision", prefijo=PREFIJO_REMISION, uow=uow
            )

            movimientos_creados = [
                await self._confirmar_item(
                    item, remision, cliente_destino, notas, confirmado_por, uow
                )
                for item in reserva.items
            ]

            await self._reserva_repository.eliminar(reserva.session_id, uow=uow)

        return movimientos_creados

    async def _confirmar_item(
        self,
        item: ItemReserva,
        remision: str,
        cliente_destino: str | None,
        notas: str | None,
        creado_por: AuditPersona,
        uow: UnitOfWorkPort,
    ) -> Movimiento:
        producto = await self._ajustador_de_stock.descontar(
            item.producto_codigo, item.ubicacion, item.cantidad, creado_por, uow
        )

        movimiento = Movimiento.registrar_salida(
            producto_codigo=item.producto_codigo,
            producto_nombre=producto.nombre,
            cantidad=item.cantidad,
            motivo="Salida pendiente confirmada",
            cliente_destino=cliente_destino,
            ubicacion=item.ubicacion,
            notas=notas,
            remision=remision,
            creado_por=creado_por,
        )
        return await self._movimiento_repository.crear(movimiento, uow=uow)
