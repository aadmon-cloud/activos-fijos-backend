from modules.auth.application.ports.usuario_repository import UsuarioRepositoryPort
from modules.auth.domain.entities.usuario import Usuario
from modules.auth.domain.errors import (
    OperacionSobrePropioUsuarioNoPermitidaError,
    UsuarioAdminNoEncontradoError,
)


class EliminarUsuarioAdminService:
    def __init__(self, usuario_repository: UsuarioRepositoryPort):
        self._usuario_repository = usuario_repository

    async def ejecutar(self, admin_actual: Usuario, usuario_id: str) -> None:
        """Raises:
        OperacionSobrePropioUsuarioNoPermitidaError: el admin intenta eliminarse a sí mismo.
        UsuarioAdminNoEncontradoError: no existe un usuario con ese id.
        """
        if usuario_id == admin_actual.id:
            raise OperacionSobrePropioUsuarioNoPermitidaError()

        eliminado = await self._usuario_repository.eliminar(usuario_id)
        if not eliminado:
            raise UsuarioAdminNoEncontradoError(usuario_id)
