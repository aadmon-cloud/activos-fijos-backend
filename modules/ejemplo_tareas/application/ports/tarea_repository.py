from abc import ABC, abstractmethod

from modules.ejemplo_tareas.domain.entities.tarea import Tarea


class TareaRepositoryPort(ABC):
    @abstractmethod
    async def guardar(self, tarea: Tarea) -> Tarea:
        """Persist the task and return the stored entity."""

    @abstractmethod
    async def obtener_por_id(self, tarea_id: str) -> Tarea | None:
        """Return a task by id or None if it does not exist."""

    @abstractmethod
    async def listar_paginado(self, pagina: int, limite: int) -> tuple[list[Tarea], int]:
        """Return a paginated slice of tasks and the total number of records."""

    @abstractmethod
    async def actualizar(self, tarea: Tarea) -> Tarea:
        """Persist the updated state of a task."""
