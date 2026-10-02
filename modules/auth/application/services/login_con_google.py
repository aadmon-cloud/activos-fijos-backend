import secrets
from datetime import UTC, datetime

from modules.auth.application.dto.resultado_login_dto import ResultadoLoginDTO
from modules.auth.application.ports.google_oauth import GoogleOAuthPort
from modules.auth.application.ports.token import TokenPort
from modules.auth.application.ports.usuario_repository import UsuarioRepositoryPort
from modules.auth.domain.entities.usuario import Usuario
from modules.auth.domain.errors import UsuarioInactivoError
from shared.domain.entities.audit_persona import AuditPersona


class LoginConGoogleService:
    def __init__(
        self,
        usuario_repository: UsuarioRepositoryPort,
        google_oauth: GoogleOAuthPort,
        token_port: TokenPort,
    ):
        self._usuario_repository = usuario_repository
        self._google_oauth = google_oauth
        self._token_port = token_port

    async def ejecutar(self, code: str) -> ResultadoLoginDTO:
        """Completa el login con Google a partir del `code` del callback.

        Busca por email o por google_id; si no existe, crea la cuenta; si existe
        pero fue creada por email/password, la enlaza con Google. Nunca permite
        elegir rol — siempre `operativo` para cuentas nuevas.

        Raises:
            GoogleOAuthNoConfiguradoError: si faltan credenciales en el servidor.
            GoogleOAuthError: si el intercambio con Google falla.
            UsuarioInactivoError: si la cuenta (nueva o existente) está desactivada.
        """
        datos = await self._google_oauth.obtener_datos_usuario(code)
        ahora = datetime.now(UTC)

        usuario = await self._usuario_repository.obtener_por_email(datos.email)
        if usuario is None:
            usuario = await self._usuario_repository.obtener_por_google_id(datos.google_id)

        if usuario is None:
            usuario = await self._crear_usuario_google(datos, ahora)
        elif not usuario.google_id or not usuario.google_picture or not usuario.email_verificado:
            usuario_vinculado = usuario.vincular_google(
                google_id=datos.google_id,
                google_picture=datos.picture,
                actualizado_por=AuditPersona(
                    id_persona=usuario.id, nombre=usuario.username, fecha=ahora
                ),
            )
            usuario = await self._usuario_repository.actualizar(usuario_vinculado)

        if not usuario.activo:
            raise UsuarioInactivoError(usuario.id)

        access_token = self._token_port.crear_token(
            {"sub": usuario.id, "rol": usuario.rol.value}
        )
        return ResultadoLoginDTO(access_token=access_token, usuario=usuario)

    async def _crear_usuario_google(self, datos, ahora) -> Usuario:
        username = datos.nombre.strip().lower().replace(" ", "_") or datos.email.split("@")[0]
        if await self._usuario_repository.existe_por_username(username):
            username = f"{username}_{secrets.token_hex(3)}"

        nuevo_usuario = Usuario.crear_desde_google(
            email=datos.email,
            username=username,
            google_id=datos.google_id,
            google_picture=datos.picture,
        )
        return await self._usuario_repository.crear(nuevo_usuario)
