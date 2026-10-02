from datetime import UTC, datetime

from modules.auth.application.dto.restablecer_password import RestablecerPasswordInput
from modules.auth.application.ports.password_hasher import PasswordHasherPort
from modules.auth.application.ports.usuario_repository import UsuarioRepositoryPort
from modules.auth.domain.errors import (
    ConfirmacionPasswordInvalidaError,
    TokenRecuperacionInvalidoError,
)
from shared.domain.entities.audit_persona import AuditPersona


class RestablecerPasswordService:
    def __init__(
        self,
        usuario_repository: UsuarioRepositoryPort,
        password_hasher: PasswordHasherPort,
    ):
        self._usuario_repository = usuario_repository
        self._password_hasher = password_hasher

    async def ejecutar(self, entrada: RestablecerPasswordInput) -> None:
        """Restablece el password usando un token de recuperación.

        Raises:
            ConfirmacionPasswordInvalidaError: new_password y confirm_password no coinciden.
            TokenRecuperacionInvalidoError: token inexistente o expirado.
        """
        if entrada.new_password != entrada.confirm_password:
            raise ConfirmacionPasswordInvalidaError()

        usuario = await self._usuario_repository.obtener_por_token_reset(entrada.token)
        ahora = datetime.now(UTC)
        if usuario is None or not usuario.token_reset_valido(entrada.token, ahora):
            raise TokenRecuperacionInvalidoError()

        nuevo_hash = self._password_hasher.hashear(entrada.new_password)
        usuario_actualizado = usuario.restablecer_password(
            password_hash=nuevo_hash,
            actualizado_por=AuditPersona(
                id_persona=usuario.id, nombre=usuario.username, fecha=ahora
            ),
        )
        await self._usuario_repository.actualizar(usuario_actualizado)
