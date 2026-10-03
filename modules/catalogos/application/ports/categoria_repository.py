from abc import ABC, abstractmethod

from modules.catalogos.domain.entities import Categoria


class CategoriaRepositoryPort(ABC):
    @abstractmethod
    async def guardar(self, categoria: Categoria) -> Categoria: ...

    @abstractmethod
    async def obtener_por_id(self, id_categoria: str) -> Categoria | None: ...

    @abstractmethod
    async def obtener_por_nombre(self, nombre: str) -> Categoria | None: ...

    @abstractmethod
    async def listar(self) -> list[Categoria]: ...

    @abstractmethod
    async def eliminar(self, id_categoria: str) -> None: ...
