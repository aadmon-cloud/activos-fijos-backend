from functools import lru_cache

from config.settings import settings

from modules.usuarios.application.ports.emisor_token import EmisorTokenPort
from modules.usuarios.application.ports.hasher import HasherPort
from modules.usuarios.application.ports.usuario_repository import UsuarioRepositoryPort
from modules.usuarios.application.ports.verificador_area import VerificadorAreaPort
from modules.usuarios.application.ports.verificador_identidad_google import (
    VerificadorIdentidadGooglePort,
)
from modules.usuarios.application.services.actualizar_usuario import ActualizarUsuarioService
from modules.usuarios.application.services.autenticar_con_google import AutenticarConGoogleService
from modules.usuarios.application.services.autenticar_usuario import AutenticarUsuarioService
from modules.usuarios.application.services.cambiar_password import CambiarPasswordService
from modules.usuarios.application.services.desactivar_usuario import DesactivarUsuarioService
from modules.usuarios.application.services.listar_directorio_usuarios import (
    ListarDirectorioUsuariosService,
)
from modules.usuarios.application.services.listar_usuarios import ListarUsuariosService
from modules.usuarios.application.services.obtener_usuario import ObtenerUsuarioService
from modules.usuarios.application.services.reactivar_usuario import ReactivarUsuarioService
from modules.usuarios.application.services.registrar_usuario import RegistrarUsuarioService
from modules.usuarios.application.services.restablecer_password import RestablecerPasswordService
from modules.usuarios.infrastructure.persistence.mongo.usuario_repository import (
    MongoUsuarioRepository,
)
from modules.usuarios.infrastructure.persistence.mongo.verificador_area import (
    MongoVerificadorArea,
)
from modules.usuarios.domain.errors import LoginConPasswordDeshabilitadoError
from modules.usuarios.infrastructure.security.bcrypt_hasher import BcryptHasher
from modules.usuarios.infrastructure.security.google_verificador_identidad import (
    GoogleVerificadorIdentidad,
)
from modules.usuarios.infrastructure.security.jwt_emisor_token import JWTEmisorToken


@lru_cache(maxsize=1)
def get_usuario_repository() -> UsuarioRepositoryPort:
    return MongoUsuarioRepository()


@lru_cache(maxsize=1)
def get_hasher() -> HasherPort:
    return BcryptHasher()


@lru_cache(maxsize=1)
def get_emisor_token() -> EmisorTokenPort:
    return JWTEmisorToken()


@lru_cache(maxsize=1)
def get_verificador_area() -> VerificadorAreaPort:
    return MongoVerificadorArea()


@lru_cache(maxsize=1)
def get_verificador_identidad_google() -> VerificadorIdentidadGooglePort:
    return GoogleVerificadorIdentidad()


def requiere_login_password_habilitado() -> None:
    """El ingreso es solo con Google: la ruta de contrasena solo existe si se reabre a proposito (pruebas locales)."""
    if not settings.LOGIN_PASSWORD_HABILITADO:
        raise LoginConPasswordDeshabilitadoError()


def get_autenticar_con_google_service() -> AutenticarConGoogleService:
    return AutenticarConGoogleService(
        usuario_repository=get_usuario_repository(),
        verificador=get_verificador_identidad_google(),
        emisor_token=get_emisor_token(),
    )


def get_registrar_usuario_service() -> RegistrarUsuarioService:
    return RegistrarUsuarioService(
        usuario_repository=get_usuario_repository(),
        hasher=get_hasher(),
        verificador_area=get_verificador_area(),
    )


def get_autenticar_usuario_service() -> AutenticarUsuarioService:
    return AutenticarUsuarioService(
        usuario_repository=get_usuario_repository(),
        hasher=get_hasher(),
        emisor_token=get_emisor_token(),
    )


def get_listar_usuarios_service() -> ListarUsuariosService:
    return ListarUsuariosService(usuario_repository=get_usuario_repository())


def get_listar_directorio_usuarios_service() -> ListarDirectorioUsuariosService:
    return ListarDirectorioUsuariosService(usuario_repository=get_usuario_repository())


def get_obtener_usuario_service() -> ObtenerUsuarioService:
    return ObtenerUsuarioService(usuario_repository=get_usuario_repository())


def get_actualizar_usuario_service() -> ActualizarUsuarioService:
    return ActualizarUsuarioService(
        usuario_repository=get_usuario_repository(),
        verificador_area=get_verificador_area(),
    )


def get_desactivar_usuario_service() -> DesactivarUsuarioService:
    return DesactivarUsuarioService(usuario_repository=get_usuario_repository())


def get_reactivar_usuario_service() -> ReactivarUsuarioService:
    return ReactivarUsuarioService(usuario_repository=get_usuario_repository())


def get_restablecer_password_service() -> RestablecerPasswordService:
    return RestablecerPasswordService(
        usuario_repository=get_usuario_repository(), hasher=get_hasher()
    )


def get_cambiar_password_service() -> CambiarPasswordService:
    return CambiarPasswordService(usuario_repository=get_usuario_repository(), hasher=get_hasher())
