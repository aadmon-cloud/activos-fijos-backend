from abc import ABC, abstractmethod

from modules.tareas.domain.entities import Tarea


class TareaRepositoryPort(ABC):
    @abstractmethod
    async def guardar(self, tarea: Tarea) -> Tarea: ...

    @abstractmethod
    async def listar(self) -> list[Tarea]: ...
