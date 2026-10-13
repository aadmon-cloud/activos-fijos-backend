from modules.usuarios.application.dto.login_google_dto import LoginGoogleDTO
from modules.usuarios.application.dto.token_dto import TokenDTO
from modules.usuarios.application.dto.usuario_dto import usuario_a_dto
from modules.usuarios.application.ports.emisor_token import EmisorTokenPort
from modules.usuarios.application.ports.usuario_repository import UsuarioRepositoryPort
from modules.usuarios.application.ports.verificador_identidad_google import (
    VerificadorIdentidadGooglePort,
)
from modules.usuarios.domain.errors import CuentaGoogleSinAccesoError


class AutenticarConGoogleService:
    """Abre la sesion de un usuario ya registrado a partir de su cuenta de Google.

    Nadie se crea solo: si el correo que Google certifica no coincide con un usuario activo, no entra. El rol y el
    area siguen siendo los que el administrador asigno al registrarlo.
    """

    def __init__(
        self,
        usuario_repository: UsuarioRepositoryPort,
        verificador: VerificadorIdentidadGooglePort,
        emisor_token: EmisorTokenPort,
    ):
        self._usuario_repository = usuario_repository
        self._verificador = verificador
        self._emisor_token = emisor_token

    async def ejecutar(self, dto: LoginGoogleDTO) -> TokenDTO:
        identidad = await self._verificador.verificar(dto.credencial, dto.nonce)

        usuario = await self._usuario_repository.obtener_por_email(identidad.email.strip().lower())
        if usuario is None or not usuario.activo:
            raise CuentaGoogleSinAccesoError()

        return TokenDTO(
            access_token=self._emisor_token.emitir(usuario),
            token_type="bearer",
            usuario=usuario_a_dto(usuario),
        )
