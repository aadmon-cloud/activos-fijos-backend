from functools import lru_cache

from modules.usuarios.application.ports.emisor_token import EmisorTokenPort
from modules.usuarios.application.ports.hasher import HasherPort
from modules.usuarios.application.ports.usuario_repository import UsuarioRepositoryPort
from modules.usuarios.application.ports.verificador_area import VerificadorAreaPort
from modules.usuarios.application.services.actualizar_usuario import ActualizarUsuarioService
from modules.usuarios.application.services.autenticar_usuario import AutenticarUsuarioService
from modules.usuarios.application.services.desactivar_usuario import DesactivarUsuarioService
from modules.usuarios.application.services.listar_usuarios import ListarUsuariosService
from modules.usuarios.application.services.obtener_usuario import ObtenerUsuarioService
from modules.usuarios.application.services.registrar_usuario import RegistrarUsuarioService
from modules.usuarios.infrastructure.persistence.mongo.usuario_repository import (
    MongoUsuarioRepository,
)
from modules.usuarios.infrastructure.persistence.mongo.verificador_area import (
    MongoVerificadorArea,
)
from modules.usuarios.infrastructure.security.bcrypt_hasher import BcryptHasher
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


def get_obtener_usuario_service() -> ObtenerUsuarioService:
    return ObtenerUsuarioService(usuario_repository=get_usuario_repository())


def get_actualizar_usuario_service() -> ActualizarUsuarioService:
    return ActualizarUsuarioService(
        usuario_repository=get_usuario_repository(),
        verificador_area=get_verificador_area(),
    )


def get_desactivar_usuario_service() -> DesactivarUsuarioService:
    return DesactivarUsuarioService(usuario_repository=get_usuario_repository())
