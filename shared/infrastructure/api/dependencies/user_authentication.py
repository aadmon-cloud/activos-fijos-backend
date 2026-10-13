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
from shared.infrastructure.security.consulta_estado_usuario_mongo import (
    ConsultaEstadoUsuarioMongo,
)
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
        if identidad.rol not in roles_permitidos:
            raise PermisosInsuficientesError()
        return identidad

    return _verificar_rol
