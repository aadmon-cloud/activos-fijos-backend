from typing import Annotated

from fastapi import Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from config.settings import settings
from modules.auth.application.dto.listar_usuarios import ListarUsuariosInput
from modules.auth.application.ports.email_sender import EmailSenderPort
from modules.auth.application.ports.google_oauth import GoogleOAuthPort
from modules.auth.application.ports.password_hasher import PasswordHasherPort
from modules.auth.application.ports.token import TokenPort
from modules.auth.application.ports.usuario_repository import UsuarioRepositoryPort
from modules.auth.application.services.actualizar_usuario_admin import (
    ActualizarUsuarioAdminService,
)
from modules.auth.application.services.cambiar_password import CambiarPasswordService
from modules.auth.application.services.crear_usuario_admin import (
    CrearUsuarioAdminService,
)
from modules.auth.application.services.eliminar_usuario_admin import (
    EliminarUsuarioAdminService,
)
from modules.auth.application.services.iniciar_login_google import (
    IniciarLoginGoogleService,
)
from modules.auth.application.services.listar_usuarios import ListarUsuariosService
from modules.auth.application.services.login import LoginService
from modules.auth.application.services.login_con_google import LoginConGoogleService
from modules.auth.application.services.registrar_usuario import RegistrarUsuarioService
from modules.auth.application.services.restablecer_password import (
    RestablecerPasswordService,
)
from modules.auth.application.services.solicitar_recuperacion_password import (
    SolicitarRecuperacionPasswordService,
)
from modules.auth.infrastructure.email.smtp_email_sender import SmtpEmailSender
from modules.auth.infrastructure.oauth.google_oauth_adapter import GoogleOAuthAdapter
from modules.auth.infrastructure.persistence.mongo.usuario_repository import (
    MongoUsuarioRepository,
)
from modules.auth.infrastructure.security.bcrypt_password_hasher import (
    BcryptPasswordHasher,
)
from modules.auth.infrastructure.security.jwt_token_adapter import JwtTokenAdapter
from shared.infrastructure.api.dependencies.mongo import get_mongo_db


def get_usuario_repository(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_mongo_db)],
) -> UsuarioRepositoryPort:
    return MongoUsuarioRepository(db)


def get_password_hasher() -> PasswordHasherPort:
    return BcryptPasswordHasher()


def get_token_port() -> TokenPort:
    return JwtTokenAdapter(
        secret_key=settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
        expira_minutos=settings.JWT_EXPIRE_MINUTES,
    )


def get_login_service(
    usuario_repository: Annotated[UsuarioRepositoryPort, Depends(get_usuario_repository)],
    password_hasher: Annotated[PasswordHasherPort, Depends(get_password_hasher)],
    token_port: Annotated[TokenPort, Depends(get_token_port)],
) -> LoginService:
    return LoginService(usuario_repository, password_hasher, token_port)


def get_registrar_usuario_service(
    usuario_repository: Annotated[UsuarioRepositoryPort, Depends(get_usuario_repository)],
    password_hasher: Annotated[PasswordHasherPort, Depends(get_password_hasher)],
) -> RegistrarUsuarioService:
    return RegistrarUsuarioService(usuario_repository, password_hasher)


def get_email_sender() -> EmailSenderPort:
    return SmtpEmailSender(
        smtp_server=settings.SMTP_SERVER,
        smtp_port=settings.SMTP_PORT,
        smtp_user=settings.SMTP_USER,
        smtp_password=settings.SMTP_PASSWORD,
        from_email=settings.FROM_EMAIL,
        frontend_url=settings.FRONTEND_URL,
    )


def get_solicitar_recuperacion_password_service(
    usuario_repository: Annotated[UsuarioRepositoryPort, Depends(get_usuario_repository)],
    email_sender: Annotated[EmailSenderPort, Depends(get_email_sender)],
) -> SolicitarRecuperacionPasswordService:
    return SolicitarRecuperacionPasswordService(usuario_repository, email_sender)


def get_restablecer_password_service(
    usuario_repository: Annotated[UsuarioRepositoryPort, Depends(get_usuario_repository)],
    password_hasher: Annotated[PasswordHasherPort, Depends(get_password_hasher)],
) -> RestablecerPasswordService:
    return RestablecerPasswordService(usuario_repository, password_hasher)


def get_cambiar_password_service(
    usuario_repository: Annotated[UsuarioRepositoryPort, Depends(get_usuario_repository)],
    password_hasher: Annotated[PasswordHasherPort, Depends(get_password_hasher)],
) -> CambiarPasswordService:
    return CambiarPasswordService(usuario_repository, password_hasher)


def get_google_oauth_port() -> GoogleOAuthPort:
    return GoogleOAuthAdapter(
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
    )


def get_iniciar_login_google_service(
    google_oauth: Annotated[GoogleOAuthPort, Depends(get_google_oauth_port)],
) -> IniciarLoginGoogleService:
    return IniciarLoginGoogleService(google_oauth)


def get_login_con_google_service(
    usuario_repository: Annotated[UsuarioRepositoryPort, Depends(get_usuario_repository)],
    google_oauth: Annotated[GoogleOAuthPort, Depends(get_google_oauth_port)],
    token_port: Annotated[TokenPort, Depends(get_token_port)],
) -> LoginConGoogleService:
    return LoginConGoogleService(usuario_repository, google_oauth, token_port)


def get_listar_usuarios_input(
    pagina: int = Query(default=1, ge=1),
    limite: int = Query(default=10, ge=1, le=100),
) -> ListarUsuariosInput:
    return ListarUsuariosInput(pagina=pagina, limite=limite)


def get_listar_usuarios_service(
    usuario_repository: Annotated[UsuarioRepositoryPort, Depends(get_usuario_repository)],
) -> ListarUsuariosService:
    return ListarUsuariosService(usuario_repository)


def get_crear_usuario_admin_service(
    usuario_repository: Annotated[UsuarioRepositoryPort, Depends(get_usuario_repository)],
    password_hasher: Annotated[PasswordHasherPort, Depends(get_password_hasher)],
) -> CrearUsuarioAdminService:
    return CrearUsuarioAdminService(usuario_repository, password_hasher)


def get_actualizar_usuario_admin_service(
    usuario_repository: Annotated[UsuarioRepositoryPort, Depends(get_usuario_repository)],
    password_hasher: Annotated[PasswordHasherPort, Depends(get_password_hasher)],
) -> ActualizarUsuarioAdminService:
    return ActualizarUsuarioAdminService(usuario_repository, password_hasher)


def get_eliminar_usuario_admin_service(
    usuario_repository: Annotated[UsuarioRepositoryPort, Depends(get_usuario_repository)],
) -> EliminarUsuarioAdminService:
    return EliminarUsuarioAdminService(usuario_repository)
