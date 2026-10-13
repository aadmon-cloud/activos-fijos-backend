from dataclasses import replace
from datetime import UTC, datetime, timedelta

from modules.movimientos.application.avisos import EventoMovimiento, avisar
from modules.movimientos.application.ports.activo_movimiento_port import ActivoMovimientoPort
from modules.movimientos.application.ports.movimiento_repository import MovimientoRepositoryPort
from shared.application.notifications.ports import NotificadorPort

# Se recuerda cuando la devolucion estimada es dentro de este plazo, o ya paso.
DIAS_AVISO_DEVOLUCION = 1


class RecordarDevolucionesMovimientoService:
    """Recuerda, una sola vez por movimiento, que se acerca la devolucion de los activos que salieron."""

    def __init__(
        self,
        movimiento_repository: MovimientoRepositoryPort,
        activo_movimiento: ActivoMovimientoPort,
        notificador: NotificadorPort,
    ):
        self._movimiento_repository = movimiento_repository
        self._activo_movimiento = activo_movimiento
        self._notificador = notificador

    async def ejecutar(self, ahora: datetime | None = None) -> int:
        limite = (ahora or datetime.now(UTC)) + timedelta(days=DIAS_AVISO_DEVOLUCION)
        pendientes = await self._movimiento_repository.listar_devoluciones_por_recordar(limite)

        for movimiento in pendientes:
            resumenes = await self._activo_movimiento.obtener_resumenes(movimiento.activo_ids)
            await avisar(self._notificador, EventoMovimiento.RECORDATORIO_DEVOLUCION, movimiento, resumenes)
            await self._movimiento_repository.guardar(
                replace(movimiento, recordatorio_devolucion_enviado=True)
            )

        return len(pendientes)
