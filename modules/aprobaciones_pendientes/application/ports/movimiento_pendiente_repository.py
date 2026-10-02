from abc import ABC, abstractmethod

from modules.aprobaciones_pendientes.application.dto.listar_movimientos_pendientes import (
    ListarMovimientosPendientesInput,
)
from modules.aprobaciones_pendientes.domain.entities.movimiento_pendiente import (
    MovimientoPendiente,
)
from shared.application.persistence.unit_of_work import UnitOfWorkPort


class MovimientoPendienteRepositoryPort(ABC):
    @abstractmethod
    async def crear(
        self, pendiente: MovimientoPendiente, uow: UnitOfWorkPort | None = None
    ) -> MovimientoPendiente:
        """Persist a new proposal and return it with its assigned id."""

    @abstractmethod
    async def obtener_por_id(self, movimiento_pendiente_id: str) -> MovimientoPendiente | None:
        """Return the proposal with this id, or None if it does not exist."""

    @abstractmethod
    async def actualizar(
        self, pendiente: MovimientoPendiente, uow: UnitOfWorkPort | None = None
    ) -> MovimientoPendiente:
        """Persist the updated state of an existing proposal (ej. al confirmarla)."""

    @abstractmethod
    async def eliminar(
        self, movimiento_pendiente_id: str, uow: UnitOfWorkPort | None = None
    ) -> None:
        """Delete a proposal by id."""

    @abstractmethod
    async def listar(
        self, filtro: ListarMovimientosPendientesInput
    ) -> tuple[list[MovimientoPendiente], int]:
        """Return a paginated, filtered slice of proposals and the total match count."""
