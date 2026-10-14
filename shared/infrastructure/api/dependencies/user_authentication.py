from dataclasses import replace
from typing import Annotated

from fastapi import Depends, Header, Request

from config.settings import settings
from shared.application.user_auth.dto import IdentidadUsuarioAutenticada
from shared.application.user_auth.errors import (
    PermisosInsuficientesError,
    SesionInvalidaError,
    SesionRequeridaError,
    TokenUsuarioInvalidoError,
)
from shared.domain.permisos import CLAVES_FUNCIONES, PERMISOS_EXCLUSIVOS_SUPER_ADMINISTRADOR
from shared.domain.roles import es_super_administrador
from shared.infrastructure.security.consulta_estado_usuario_mongo import (
    ConsultaEstadoUsuarioMongo,
)
from shared.infrastructure.security.consulta_permisos_rol_mongo import consulta_permisos_rol
from shared.infrastructure.security.verificador_token_usuario_jwt import (
    VerificadorTokenUsuarioJWT,
)

_verificador = VerificadorTokenUsuarioJWT()
_consulta_estado = ConsultaEstadoUsuarioMongo()


def _extraer_token(request: Request, authorization: str | None) -> str | None:
    token_cookie = request.cookies.get(settings.COOKIE_NAME)
    if token_cookie:
        return token_cookie

    if authorization and authorization.startswith("Bearer "):
        return authorization.removeprefix("Bearer ").strip()

    return None


async def requiere_usuario_autenticado(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> IdentidadUsuarioAutenticada:
    token = _extraer_token(request, authorization)
    if not token:
        raise SesionRequeridaError()

    try:
        identidad = _verificador.verificar(token)
    except TokenUsuarioInvalidoError as exc:
        raise SesionInvalidaError() from exc

    # El token es valido, pero el usuario pudo desactivarse o cambiar de rol despues de emitirlo.
    estado = await _consulta_estado.obtener(identidad.id_usuario)
    if estado is None or not estado.activo:
        raise SesionInvalidaError()

    # Rol y area vigentes (no los del token): un cambio en el usuario surte efecto de inmediato.
    return replace(identidad, rol=estado.rol, area_id=estado.area_id)


def requiere_rol(*roles_permitidos: str):
    def _verificar_rol(
        identidad: Annotated[
            IdentidadUsuarioAutenticada, Depends(requiere_usuario_autenticado)
        ],
    ) -> IdentidadUsuarioAutenticada:
        # El Super administrador pasa cualquier guardia de rol: es el rol de mayor jerarquia.
        if not es_super_administrador(identidad.rol) and identidad.rol not in roles_permitidos:
            raise PermisosInsuficientesError()
        return identidad

    return _verificar_rol


async def requiere_super_administrador(
    identidad: Annotated[IdentidadUsuarioAutenticada, Depends(requiere_usuario_autenticado)],
) -> IdentidadUsuarioAutenticada:
    """Solo el Super administrador: administra la matriz de permisos y a otros super administradores."""
    if not es_super_administrador(identidad.rol):
        raise PermisosInsuficientesError()
    return identidad


async def tiene_permiso(rol: str, clave: str) -> bool:
    """Si el rol tiene habilitada la funcion `clave`. Para reglas que dependen de una funcion y no cortan toda la ruta."""
    return clave in await consulta_permisos_rol.obtener(rol)


_CLAVES_VALIDAS = CLAVES_FUNCIONES | frozenset(PERMISOS_EXCLUSIVOS_SUPER_ADMINISTRADOR)


def requiere_permiso(clave: str):
    """Deja pasar a quien tenga habilitada la funcion `clave` en la matriz de permisos de su rol.

    El Super administrador siempre la tiene. Una clave que no existe en el catalogo falla al arrancar, no en produccion.
    """
    if clave not in _CLAVES_VALIDAS:
        raise ValueError(f"La funcion '{clave}' no existe en el catalogo de permisos.")

    async def _verificar_permiso(
        identidad: Annotated[IdentidadUsuarioAutenticada, Depends(requiere_usuario_autenticado)],
    ) -> IdentidadUsuarioAutenticada:
        permisos = await consulta_permisos_rol.obtener(identidad.rol)
        if clave not in permisos:
            raise PermisosInsuficientesError()
        return identidad

    return _verificar_permiso
