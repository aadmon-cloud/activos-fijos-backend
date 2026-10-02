from modules.auth.application.dto.login import LoginInput
from modules.auth.application.dto.resultado_login_dto import ResultadoLoginDTO
from modules.auth.application.ports.password_hasher import PasswordHasherPort
from modules.auth.application.ports.token import TokenPort
from modules.auth.application.ports.usuario_repository import UsuarioRepositoryPort
from modules.auth.domain.errors import CredencialesInvalidasError, UsuarioInactivoError


class LoginService:
    def __init__(
        self,
        usuario_repository: UsuarioRepositoryPort,
        password_hasher: PasswordHasherPort,
        token_port: TokenPort,
    ):
        self._usuario_repository = usuario_repository
        self._password_hasher = password_hasher
        self._token_port = token_port

    async def ejecutar(self, entrada: LoginInput) -> ResultadoLoginDTO:
        """Autentica por email/password y emite un token.

        Raises:
            CredencialesInvalidasError: Email inexistente, sin password (cuenta
                solo-Google) o password incorrecto. Mismo error en los tres casos
                para no revelar cuál de las dos falló.
            UsuarioInactivoError: La cuenta existe pero está desactivada.
        """
        email = entrada.email.strip().lower()
        usuario = await self._usuario_repository.obtener_por_email(email)

        if not usuario or not usuario.password_hash:
            raise CredencialesInvalidasError()

        if not self._password_hasher.verificar(entrada.password, usuario.password_hash):
            raise CredencialesInvalidasError()

        if not usuario.activo:
            raise UsuarioInactivoError(usuario.id)

        access_token = self._token_port.crear_token(
            {"sub": usuario.id, "rol": usuario.rol.value}
        )
        return ResultadoLoginDTO(access_token=access_token, usuario=usuario)
