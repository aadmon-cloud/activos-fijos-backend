from modules.usuarios.application.dto.login_dto import LoginDTO
from modules.usuarios.application.dto.token_dto import TokenDTO
from modules.usuarios.application.dto.usuario_dto import usuario_a_dto
from modules.usuarios.application.ports.emisor_token import EmisorTokenPort
from modules.usuarios.application.ports.hasher import HasherPort
from modules.usuarios.application.ports.usuario_repository import UsuarioRepositoryPort
from modules.usuarios.domain.errors import CredencialesInvalidasError


class AutenticarUsuarioService:
    def __init__(
        self,
        usuario_repository: UsuarioRepositoryPort,
        hasher: HasherPort,
        emisor_token: EmisorTokenPort,
    ):
        self._usuario_repository = usuario_repository
        self._hasher = hasher
        self._emisor_token = emisor_token

    async def ejecutar(self, dto: LoginDTO) -> TokenDTO:
        email = dto.email.strip().lower()
        usuario = await self._usuario_repository.obtener_por_email(email)

        credenciales_validas = usuario is not None and self._hasher.verificar(
            dto.password, usuario.password_hash
        )
        if not credenciales_validas or not usuario.activo:
            raise CredencialesInvalidasError()

        token = self._emisor_token.emitir(usuario)

        return TokenDTO(
            access_token=token,
            token_type="bearer",
            usuario=usuario_a_dto(usuario),
        )
