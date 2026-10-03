from abc import ABC, abstractmethod

from modules.catalogos.domain.entities import Area


class AreaRepositoryPort(ABC):
    @abstractmethod
    async def guardar(self, area: Area) -> Area: ...

    @abstractmethod
    async def obtener_por_id(self, id_area: str) -> Area | None: ...

    @abstractmethod
    async def obtener_por_nombre(self, nombre: str) -> Area | None: ...

    @abstractmethod
    async def listar(self) -> list[Area]: ...

    @abstractmethod
    async def eliminar(self, id_area: str) -> None: ...
