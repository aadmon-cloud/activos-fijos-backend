from modules.reservas.application.ports.reserva_repository import ReservaRepositoryPort
from modules.reservas.domain.entities.reserva import Reserva
from modules.reservas.domain.errors import ReservaNoEncontradaError


class ObtenerReservaService:
    def __init__(self, reserva_repository: ReservaRepositoryPort):
        self._reserva_repository = reserva_repository

    async def ejecutar(self, session_id: str) -> Reserva:
        """Raises:
        ReservaNoEncontradaError: no existe una reserva para esa sesión.
        """
        reserva = await self._reserva_repository.obtener_por_session_id(session_id)
        if reserva is None:
            raise ReservaNoEncontradaError(session_id)
        return reserva
