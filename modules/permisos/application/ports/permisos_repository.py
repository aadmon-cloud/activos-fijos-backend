from abc import ABC, abstractmethod

from modules.permisos.domain.entities import CambioPermiso, PermisosRol


class PermisosRolRepositoryPort(ABC):
    @abstractmethod
    async def obtener(self, rol: str) -> PermisosRol | None: ...

    @abstractmethod
    async def listar(self) -> list[PermisosRol]: ...

    @abstractmethod
    async def guardar(self, permisos_rol: PermisosRol) -> PermisosRol:
        """Crea o reemplaza el documento del rol (uno por rol)."""

    @abstractmethod
    async def registrar_cambios(self, cambios: list[CambioPermiso]) -> None: ...

    @abstractmethod
    async def listar_historial(self, rol: str | None, skip: int, limit: int) -> list[CambioPermiso]:
        """Del cambio mas reciente al mas antiguo."""
