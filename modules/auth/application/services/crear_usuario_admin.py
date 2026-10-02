import secrets
from datetime import UTC, datetime

from modules.auth.application.dto.crear_usuario_admin import CrearUsuarioAdminInput
from modules.auth.application.ports.password_hasher import PasswordHasherPort
from modules.auth.application.ports.usuario_repository import UsuarioRepositoryPort
from modules.auth.domain.entities.usuario import Usuario
from modules.auth.domain.errors import EmailYaRegistradoError
from shared.domain.entities.audit_persona import AuditPersona


class CrearUsuarioAdminService:
    def __init__(
        self,
        usuario_repository: UsuarioRepositoryPort,
        password_hasher: PasswordHasherPort,
    ):
        self._usuario_repository = usuario_repository
        self._password_hasher = password_hasher

    async def ejecutar(
        self, admin_actual: Usuario, entrada: CrearUsuarioAdminInput
    ) -> Usuario:
        """Crea un usuario con el rol elegido explícitamente por un super_admin
        (a diferencia del registro público, que siempre fuerza `operativo`).

        Raises:
            EmailYaRegistradoError: el email ya está registrado.
        """
        email = entrada.email.strip().lower()
        if await self._usuario_repository.existe_por_email(email):
            raise EmailYaRegistradoError(email)

        username = (entrada.username or email.split("@")[0]).strip().lower()
        if await self._usuario_repository.existe_por_username(username):
            username = f"{username}_{secrets.token_hex(3)}"

        password_hash = (
            self._password_hasher.hashear(entrada.password) if entrada.password else None
        )

        nuevo_usuario = Usuario.crear_por_admin(
            email=email,
            username=username,
            password_hash=password_hash,
            rol=entrada.rol,
            creado_por=AuditPersona(
                id_persona=admin_actual.id,
                nombre=admin_actual.username,
                fecha=datetime.now(UTC),
            ),
        )
        return await self._usuario_repository.crear(nuevo_usuario)
