from modules.movimientos.application.services._deteccion_modalidad import (
    detectar_modalidad_reserva,
)
from modules.movimientos.application.services.confirmar_reserva_kit import (
    ConfirmarReservaKitService,
)
from modules.movimientos.application.services.confirmar_reserva_multiple import (
    ConfirmarReservaMultipleService,
)
from modules.movimientos.application.services.confirmar_reserva_normal import (
    ConfirmarReservaNormalService,
)
from modules.movimientos.domain.entities.movimiento import Movimiento
from modules.movimientos.domain.errors import ModalidadReservaNoSoportadaError
from modules.reservas.application.ports.reserva_repository import ReservaRepositoryPort
from modules.reservas.domain.errors import ReservaNoEncontradaError
from shared.domain.entities.audit_persona import AuditPersona


class ConfirmarReservaService:
    """Dispatcher: lee la reserva una sola vez, detecta su modalidad, y
    delega a la estrategia correspondiente. Implementa la "interfaz común"
    que MIGRATION_PLAN.md proponía para las 3 modalidades — normal, kit y
    múltiple, las 3 ya soportadas."""

    def __init__(
        self,
        reserva_repository: ReservaRepositoryPort,
        confirmar_normal_service: ConfirmarReservaNormalService,
        confirmar_kit_service: ConfirmarReservaKitService,
        confirmar_multiple_service: ConfirmarReservaMultipleService,
    ):
        self._reserva_repository = reserva_repository
        self._confirmar_normal_service = confirmar_normal_service
        self._confirmar_kit_service = confirmar_kit_service
        self._confirmar_multiple_service = confirmar_multiple_service

    async def ejecutar(self, session_id: str, confirmado_por: AuditPersona) -> list[Movimiento]:
        """Raises:
        ReservaNoEncontradaError: no existe una reserva para esa sesión.
        ModalidadReservaNoSoportadaError: la reserva es una modalidad desconocida.
        """
        reserva = await self._reserva_repository.obtener_por_session_id(session_id)
        if reserva is None:
            raise ReservaNoEncontradaError(session_id)

        modalidad = detectar_modalidad_reserva(reserva.datos_adicionales or {})

        if modalidad == "normal":
            return await self._confirmar_normal_service.ejecutar(reserva, confirmado_por)
        if modalidad == "kit":
            movimiento = await self._confirmar_kit_service.ejecutar(reserva, confirmado_por)
            return [movimiento]
        if modalidad == "multiple":
            movimiento = await self._confirmar_multiple_service.ejecutar(reserva, confirmado_por)
            return [movimiento]

        raise ModalidadReservaNoSoportadaError(session_id, modalidad)
