import secrets

from modules.auth.application.dto.registrar_usuario import RegistrarUsuarioInput
from modules.auth.application.ports.password_hasher import PasswordHasherPort
from modules.auth.application.ports.usuario_repository import UsuarioRepositoryPort
from modules.auth.domain.entities.usuario import Usuario
from modules.auth.domain.errors import (
    ConfirmacionPasswordInvalidaError,
    EmailYaRegistradoError,
)


class RegistrarUsuarioService:
    def __init__(
        self,
        usuario_repository: UsuarioRepositoryPort,
        password_hasher: PasswordHasherPort,
    ):
        self._usuario_repository = usuario_repository
        self._password_hasher = password_hasher

    async def ejecutar(self, entrada: RegistrarUsuarioInput) -> Usuario:
        """Registra un usuario público. El rol siempre queda en `operativo`,
        sin importar lo que envíe el cliente (no se acepta `rol` como parámetro).

        Raises:
            ConfirmacionPasswordInvalidaError: password y confirm_password no coinciden.
            EmailYaRegistradoError: el email ya está registrado.
        """
        if entrada.password != entrada.confirm_password:
            raise ConfirmacionPasswordInvalidaError()

        email = entrada.email.strip().lower()
        if await self._usuario_repository.existe_por_email(email):
            raise EmailYaRegistradoError(email)

        username = (entrada.username or email.split("@")[0]).strip().lower()
        if await self._usuario_repository.existe_por_username(username):
            username = f"{username}_{secrets.token_hex(3)}"

        password_hash = self._password_hasher.hashear(entrada.password)
        usuario = Usuario.crear(email=email, username=username, password_hash=password_hash)
        return await self._usuario_repository.crear(usuario)
