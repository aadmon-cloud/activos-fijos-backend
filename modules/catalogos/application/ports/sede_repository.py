from abc import ABC, abstractmethod

from modules.catalogos.domain.entities import Sede


class SedeRepositoryPort(ABC):
    @abstractmethod
    async def guardar(self, sede: Sede) -> Sede: ...

    @abstractmethod
    async def obtener_por_id(self, id_sede: str) -> Sede | None: ...

    @abstractmethod
    async def obtener_por_nombre(self, nombre: str) -> Sede | None: ...

    @abstractmethod
    async def listar(self) -> list[Sede]: ...

    @abstractmethod
    async def eliminar(self, id_sede: str) -> None: ...
