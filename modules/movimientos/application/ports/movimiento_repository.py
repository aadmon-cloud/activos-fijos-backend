from abc import ABC, abstractmethod

from modules.movimientos.application.dto.exportar_movimientos_excel import (
    ExportarMovimientosExcelInput,
)
from modules.movimientos.application.dto.listar_movimientos import ListarMovimientosInput
from modules.movimientos.domain.entities.movimiento import Movimiento
from shared.application.persistence.unit_of_work import UnitOfWorkPort


class MovimientoRepositoryPort(ABC):
    @abstractmethod
    async def crear(self, movimiento: Movimiento, uow: UnitOfWorkPort | None = None) -> Movimiento:
        """Persist a new movement and return it with its assigned id."""

    @abstractmethod
    async def obtener_por_id(self, movimiento_id: str) -> Movimiento | None:
        """Return the movement with this id, or None if it does not exist."""

    @abstractmethod
    async def actualizar(
        self, movimiento: Movimiento, uow: UnitOfWorkPort | None = None
    ) -> Movimiento:
        """Persist the updated state of an existing movement (ej. adjuntar un PDF firmado)."""

    @abstractmethod
    async def listar(
        self, filtro: ListarMovimientosInput
    ) -> tuple[list[Movimiento], int]:
        """Return a paginated, filtered slice of movements and the total match count."""

    @abstractmethod
    async def listar_para_exportar(
        self, filtro: ExportarMovimientosExcelInput
    ) -> list[Movimiento]:
        """Return every movement matching this filter, unpaginated (for Excel export)."""
