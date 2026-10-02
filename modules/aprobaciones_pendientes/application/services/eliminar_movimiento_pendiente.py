from modules.aprobaciones_pendientes.application.ports.movimiento_pendiente_repository import (
    MovimientoPendienteRepositoryPort,
)
from modules.aprobaciones_pendientes.domain.errors import (
    MovimientoPendienteNoEncontradoError,
    PendienteNoPerteneceAlUsuarioError,
)


class EliminarMovimientoPendienteService:
    def __init__(self, movimiento_pendiente_repository: MovimientoPendienteRepositoryPort):
        self._movimiento_pendiente_repository = movimiento_pendiente_repository

    async def ejecutar(
        self, movimiento_pendiente_id: str, usuario_actual_id: str, es_super_admin: bool
    ) -> None:
        """Raises:
        MovimientoPendienteNoEncontradoError: no existe una propuesta con ese id.
        PendienteNoPerteneceAlUsuarioError: no es el dueño ni super_admin.
        MovimientoPendienteYaConfirmadoError: la propuesta ya fue confirmada.
        """
        pendiente = await self._movimiento_pendiente_repository.obtener_por_id(
            movimiento_pendiente_id
        )
        if pendiente is None:
            raise MovimientoPendienteNoEncontradoError(movimiento_pendiente_id)

        if not es_super_admin and not pendiente.pertenece_a(usuario_actual_id):
            raise PendienteNoPerteneceAlUsuarioError(movimiento_pendiente_id)

        pendiente.exigir_eliminable()

        await self._movimiento_pendiente_repository.eliminar(movimiento_pendiente_id)
