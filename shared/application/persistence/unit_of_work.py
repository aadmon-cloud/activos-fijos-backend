from abc import ABC, abstractmethod
from typing import Any, Callable


class UnitOfWorkPort(ABC):
    @abstractmethod
    async def __aenter__(self):
        """Start a session and transaction."""

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Commit on success or rollback on failure."""

    @property
    @abstractmethod
    def session(self) -> Any:
        """Expose the active session for repository adapters."""


IUnitOfWork = UnitOfWorkPort

# Los servicios reciben una fábrica (no una instancia concreta) para poder abrir
# una unidad de trabajo nueva por cada operación, sin acoplar `application/` al
# adaptador concreto (ej. `MongoUnitOfWork`, que vive en `infrastructure/`).
UnitOfWorkFactory = Callable[[], UnitOfWorkPort]
