from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from modules.auth.application.ports.token import TokenPort
from modules.auth.application.ports.usuario_repository import UsuarioRepositoryPort
from modules.auth.domain.entities.usuario import RolUsuario, Usuario
from modules.auth.domain.errors import (
    PermisoInsuficienteError,
    TokenInvalidoError,
    UsuarioInactivoError,
    UsuarioNoEncontradoError,
)
from modules.auth.infrastructure.api.dependencies import (
    get_token_port,
    get_usuario_repository,
)

security = HTTPBearer()


async def get_current_usuario(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    token_port: Annotated[TokenPort, Depends(get_token_port)],
    usuario_repository: Annotated[UsuarioRepositoryPort, Depends(get_usuario_repository)],
) -> Usuario:
    """Resuelve el usuario autenticado a partir del Bearer token.

    Vive en `shared/` porque todos los módulos protegidos la consumen, no solo
    `auth` (ver MIGRATION_PLAN.md, Fase 0 de `auth`). Internamente sí depende
    de los puertos de `auth`, expuestos vía `modules/auth/infrastructure/api/dependencies.py`.

    Raises:
        TokenInvalidoError: Token ausente, corrupto o expirado.
        UsuarioNoEncontradoError: El `sub` del token no corresponde a ningún usuario.
        UsuarioInactivoError: La cuenta existe pero está desactivada.
    """
    payload = token_port.decodificar_token(credentials.credentials)
    if payload is None:
        raise TokenInvalidoError()

    usuario_id = payload.get("sub")
    if not usuario_id:
        raise TokenInvalidoError()

    usuario = await usuario_repository.obtener_por_id(usuario_id)
    if usuario is None:
        raise UsuarioNoEncontradoError(usuario_id)

    if not usuario.activo:
        raise UsuarioInactivoError(usuario.id)

    return usuario


def require_roles(roles_permitidos: list[RolUsuario]):
    """Factory de dependencia: exige que el usuario autenticado tenga uno de estos roles."""

    async def verificar_rol(
        usuario: Annotated[Usuario, Depends(get_current_usuario)],
    ) -> Usuario:
        if usuario.rol not in roles_permitidos:
            raise PermisoInsuficienteError([rol.value for rol in roles_permitidos])
        return usuario

    return verificar_rol


require_authenticated = require_roles(
    [RolUsuario.SUPER_ADMIN, RolUsuario.ADMIN, RolUsuario.OPERATIVO]
)
require_admin_or_super = require_roles([RolUsuario.SUPER_ADMIN, RolUsuario.ADMIN])
require_super_admin = require_roles([RolUsuario.SUPER_ADMIN])
