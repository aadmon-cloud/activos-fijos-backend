from abc import ABC, abstractmethod

from modules.usuarios.domain.entities import Usuario


class UsuarioRepositoryPort(ABC):
    @abstractmethod
    async def guardar(self, usuario: Usuario) -> Usuario: ...

    @abstractmethod
    async def obtener_por_id(self, id_usuario: str) -> Usuario | None: ...

    @abstractmethod
    async def obtener_por_email(self, email: str) -> Usuario | None: ...

    @abstractmethod
    async def obtener_por_identificacion(self, identificacion: str) -> Usuario | None: ...

    @abstractmethod
    async def listar(self, busqueda: str | None, skip: int, limit: int) -> list[Usuario]: ...
