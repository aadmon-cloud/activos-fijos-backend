from abc import ABC, abstractmethod

from modules.reservas.domain.entities.reserva import Reserva
from shared.application.persistence.unit_of_work import UnitOfWorkPort


class ReservaRepositoryPort(ABC):
    @abstractmethod
    async def obtener_por_session_id(self, session_id: str) -> Reserva | None:
        """Return the reservation for this session, or None if it does not exist."""

    @abstractmethod
    async def crear(self, reserva: Reserva) -> Reserva:
        """Persist a new reservation and return it with its assigned id."""

    @abstractmethod
    async def actualizar(
        self, reserva: Reserva, uow: UnitOfWorkPort | None = None
    ) -> Reserva:
        """Persist the updated state of an existing reservation.

        `uow`: cuando se provee, la escritura participa de esa transacción
        (ej. `movimientos` confirmando la reserva junto con el descuento de
        stock). Sin `uow`, es una escritura suelta como cualquier otra.
        """

    @abstractmethod
    async def eliminar(self, session_id: str, uow: UnitOfWorkPort | None = None) -> bool:
        """Delete the reservation for this session. Return whether one was deleted."""

    @abstractmethod
    async def listar_activas_por_producto_ubicacion(
        self, producto_codigo: str, ubicacion: str
    ) -> list[Reserva]:
        """Return every reservation holding at least one item for this product/location."""
