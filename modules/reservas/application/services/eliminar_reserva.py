from modules.reservas.application.ports.reserva_repository import ReservaRepositoryPort
from modules.reservas.domain.errors import ReservaNoEncontradaError


class EliminarReservaService:
    def __init__(self, reserva_repository: ReservaRepositoryPort):
        self._reserva_repository = reserva_repository

    async def ejecutar(self, session_id: str) -> None:
        """Raises:
        ReservaNoEncontradaError: no existe una reserva para esa sesión.
        """
        eliminado = await self._reserva_repository.eliminar(session_id)
        if not eliminado:
            raise ReservaNoEncontradaError(session_id)
