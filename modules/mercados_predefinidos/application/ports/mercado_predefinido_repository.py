from abc import ABC, abstractmethod

from modules.mercados_predefinidos.domain.entities.mercado_predefinido import (
    MercadoPredefinido,
)


class MercadoPredefinidoRepositoryPort(ABC):
    @abstractmethod
    async def obtener_por_nombre(self, nombre: str) -> MercadoPredefinido | None:
        """Return the kit with this name, or None if it does not exist."""

    @abstractmethod
    async def existe_por_nombre(self, nombre: str) -> bool:
        """Return whether a kit with this name already exists."""

    @abstractmethod
    async def crear(self, mercado: MercadoPredefinido) -> MercadoPredefinido:
        """Persist a new kit and return it with its assigned id."""

    @abstractmethod
    async def actualizar(self, mercado: MercadoPredefinido) -> MercadoPredefinido:
        """Persist the updated state of an existing kit."""

    @abstractmethod
    async def listar(self, solo_activos: bool = True) -> list[MercadoPredefinido]:
        """Return every kit, optionally filtered to active ones only."""
