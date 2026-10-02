from datetime import UTC, datetime

from modules.auth.application.dto.cambiar_password import CambiarPasswordInput
from modules.auth.application.ports.password_hasher import PasswordHasherPort
from modules.auth.application.ports.usuario_repository import UsuarioRepositoryPort
from modules.auth.domain.entities.usuario import Usuario
from modules.auth.domain.errors import (
    ConfirmacionPasswordInvalidaError,
    PasswordActualIncorrectaError,
)
from shared.domain.entities.audit_persona import AuditPersona


class CambiarPasswordService:
    def __init__(
        self,
        usuario_repository: UsuarioRepositoryPort,
        password_hasher: PasswordHasherPort,
    ):
        self._usuario_repository = usuario_repository
        self._password_hasher = password_hasher

    async def ejecutar(self, usuario_actual: Usuario, entrada: CambiarPasswordInput) -> None:
        """Cambia el password del usuario autenticado.

        Raises:
            ConfirmacionPasswordInvalidaError: new_password y confirm_password no coinciden.
            PasswordActualIncorrectaError: current_password no coincide (o la cuenta no tiene password, p. ej. solo-Google).
        """
        if entrada.new_password != entrada.confirm_password:
            raise ConfirmacionPasswordInvalidaError()

        if not usuario_actual.password_hash or not self._password_hasher.verificar(
            entrada.current_password, usuario_actual.password_hash
        ):
            raise PasswordActualIncorrectaError()

        nuevo_hash = self._password_hasher.hashear(entrada.new_password)
        ahora = datetime.now(UTC)
        usuario_actualizado = usuario_actual.cambiar_password(
            password_hash=nuevo_hash,
            actualizado_por=AuditPersona(
                id_persona=usuario_actual.id, nombre=usuario_actual.username, fecha=ahora
            ),
        )
        await self._usuario_repository.actualizar(usuario_actualizado)
