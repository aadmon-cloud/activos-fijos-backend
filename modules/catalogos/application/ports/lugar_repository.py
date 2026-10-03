from abc import ABC, abstractmethod

from modules.catalogos.domain.entities import Lugar


class LugarRepositoryPort(ABC):
    @abstractmethod
    async def guardar(self, lugar: Lugar) -> Lugar: ...

    @abstractmethod
    async def obtener_por_id(self, id_lugar: str) -> Lugar | None: ...

    @abstractmethod
    async def obtener_por_nombre_y_sede(self, sede_id: str, nombre: str) -> Lugar | None: ...

    @abstractmethod
    async def listar(self, sede_id: str | None) -> list[Lugar]: ...

    @abstractmethod
    async def existe_alguno_con_sede(self, sede_id: str) -> bool: ...

    @abstractmethod
    async def eliminar(self, id_lugar: str) -> None: ...
