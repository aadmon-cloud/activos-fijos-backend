from abc import ABC, abstractmethod

from modules.auth.domain.entities.usuario import Usuario


class UsuarioRepositoryPort(ABC):
    @abstractmethod
    async def obtener_por_email(self, email: str) -> Usuario | None:
        """Return the user with this email, or None if it does not exist."""

    @abstractmethod
    async def obtener_por_id(self, usuario_id: str) -> Usuario | None:
        """Return the user with this id, or None if it does not exist."""

    @abstractmethod
    async def existe_por_email(self, email: str) -> bool:
        """Return whether a user with this email already exists."""

    @abstractmethod
    async def existe_por_username(self, username: str) -> bool:
        """Return whether a user with this username already exists."""

    @abstractmethod
    async def obtener_por_token_reset(self, token: str) -> Usuario | None:
        """Return the user holding this reset-password token, or None if none does."""

    @abstractmethod
    async def obtener_por_google_id(self, google_id: str) -> Usuario | None:
        """Return the user linked to this Google id, or None if none is."""

    @abstractmethod
    async def crear(self, usuario: Usuario) -> Usuario:
        """Persist a new user and return it with its assigned id."""

    @abstractmethod
    async def actualizar(self, usuario: Usuario) -> Usuario:
        """Persist the updated state of an existing user."""

    @abstractmethod
    async def listar_paginado(self, pagina: int, limite: int) -> tuple[list[Usuario], int]:
        """Return a paginated slice of users and the total number of records."""

    @abstractmethod
    async def eliminar(self, usuario_id: str) -> bool:
        """Delete the user with this id. Return whether a document was deleted."""
