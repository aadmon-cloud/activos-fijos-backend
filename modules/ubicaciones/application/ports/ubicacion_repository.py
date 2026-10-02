from abc import ABC, abstractmethod

from modules.ubicaciones.domain.entities.ubicacion import Ubicacion
from shared.application.persistence.unit_of_work import UnitOfWorkPort


class UbicacionRepositoryPort(ABC):
    @abstractmethod
    async def obtener(self, producto_codigo: str, ubicacion: str) -> Ubicacion | None:
        """Return the location for this product, or None if it does not exist."""

    @abstractmethod
    async def existe(self, producto_codigo: str, ubicacion: str) -> bool:
        """Return whether this product already has a location with this name."""

    @abstractmethod
    async def listar_por_producto(
        self, producto_codigo: str, uow: UnitOfWorkPort | None = None
    ) -> list[Ubicacion]:
        """Return every location registered for this product."""

    @abstractmethod
    async def crear(self, ubicacion: Ubicacion, uow: UnitOfWorkPort | None = None) -> Ubicacion:
        """Persist a new location and return it with its assigned id."""

    @abstractmethod
    async def actualizar(
        self, ubicacion: Ubicacion, uow: UnitOfWorkPort | None = None
    ) -> Ubicacion:
        """Persist the updated state of an existing location."""

    @abstractmethod
    async def eliminar(
        self, producto_codigo: str, ubicacion: str, uow: UnitOfWorkPort | None = None
    ) -> bool:
        """Delete this location. Return whether a document was deleted."""
