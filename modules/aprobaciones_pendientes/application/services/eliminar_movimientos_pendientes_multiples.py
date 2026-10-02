from modules.aprobaciones_pendientes.application.ports.movimiento_pendiente_repository import (
    MovimientoPendienteRepositoryPort,
)


class EliminarMovimientosPendientesMultiplesService:
    """Exclusivo `super_admin` (ya aplicado a nivel de ruta) — sin chequeo de
    dueño individual, mismo alcance que el legacy. A diferencia del legacy,
    no elimina propuestas ya confirmadas (se preserva su historial, mismo
    criterio que `EliminarMovimientoPendienteService`)."""

    def __init__(self, movimiento_pendiente_repository: MovimientoPendienteRepositoryPort):
        self._movimiento_pendiente_repository = movimiento_pendiente_repository

    async def ejecutar(self, movimientos_pendientes_ids: list[str]) -> dict:
        eliminadas = 0
        for movimiento_pendiente_id in movimientos_pendientes_ids:
            pendiente = await self._movimiento_pendiente_repository.obtener_por_id(
                movimiento_pendiente_id
            )
            if pendiente is None or pendiente.estado != "pendiente":
                continue
            await self._movimiento_pendiente_repository.eliminar(movimiento_pendiente_id)
            eliminadas += 1

        return {
            "eliminadas": eliminadas,
            "total_solicitadas": len(movimientos_pendientes_ids),
        }
