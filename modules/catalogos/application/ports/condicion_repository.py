from abc import ABC, abstractmethod

from modules.catalogos.domain.entities import Condicion


class CondicionRepositoryPort(ABC):
    @abstractmethod
    async def guardar(self, condicion: Condicion) -> Condicion: ...

    @abstractmethod
    async def obtener_por_id(self, id_condicion: str) -> Condicion | None: ...

    @abstractmethod
    async def obtener_por_nombre(self, nombre: str) -> Condicion | None: ...

    @abstractmethod
    async def listar(self) -> list[Condicion]: ...

    @abstractmethod
    async def eliminar(self, id_condicion: str) -> None: ...
