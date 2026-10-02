from datetime import UTC, datetime

from modules.auth.application.dto.actualizar_usuario_admin import (
    ActualizarUsuarioAdminInput,
)
from modules.auth.application.ports.password_hasher import PasswordHasherPort
from modules.auth.application.ports.usuario_repository import UsuarioRepositoryPort
from modules.auth.domain.entities.usuario import Usuario
from modules.auth.domain.errors import (
    OperacionSobrePropioUsuarioNoPermitidaError,
    UsuarioAdminNoEncontradoError,
)
from shared.domain.entities.audit_persona import AuditPersona


class ActualizarUsuarioAdminService:
    def __init__(
        self,
        usuario_repository: UsuarioRepositoryPort,
        password_hasher: PasswordHasherPort,
    ):
        self._usuario_repository = usuario_repository
        self._password_hasher = password_hasher

    async def ejecutar(
        self,
        admin_actual: Usuario,
        usuario_id: str,
        entrada: ActualizarUsuarioAdminInput,
    ) -> Usuario:
        """Update parcial de un usuario por un super_admin.

        Raises:
            OperacionSobrePropioUsuarioNoPermitidaError: el admin intenta editarse a sí mismo.
            UsuarioAdminNoEncontradoError: no existe un usuario con ese id.
        """
        if usuario_id == admin_actual.id:
            raise OperacionSobrePropioUsuarioNoPermitidaError()

        usuario = await self._usuario_repository.obtener_por_id(usuario_id)
        if usuario is None:
            raise UsuarioAdminNoEncontradoError(usuario_id)

        password_hash = (
            self._password_hasher.hashear(entrada.password) if entrada.password else None
        )

        usuario_actualizado = usuario.actualizar_admin(
            actualizado_por=AuditPersona(
                id_persona=admin_actual.id,
                nombre=admin_actual.username,
                fecha=datetime.now(UTC),
            ),
            username=entrada.username,
            rol=entrada.rol,
            activo=entrada.activo,
            password_hash=password_hash,
        )
        return await self._usuario_repository.actualizar(usuario_actualizado)
