from abc import ABC, abstractmethod

from shared.application.user_auth.dto import EstadoUsuario, IdentidadUsuarioAutenticada


class VerificadorTokenUsuarioPort(ABC):
    @abstractmethod
    def verificar(self, token: str) -> IdentidadUsuarioAutenticada: ...


class ConsultaEstadoUsuarioPort(ABC):
    """Consulta el estado vigente de un usuario (activo y rol actual).

    El JWT es sin estado: sin esta consulta un usuario desactivado, o con el rol
    cambiado, seguiria usando los permisos que trae su token hasta que expire.
    """

    @abstractmethod
    async def obtener(self, id_usuario: str) -> EstadoUsuario | None: ...


class ConsultaPermisosRolPort(ABC):
    """Consulta las funciones que tiene habilitadas un rol en la matriz de permisos."""

    @abstractmethod
    async def obtener(self, rol: str) -> frozenset[str]: ...
