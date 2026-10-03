from typing import Annotated

from fastapi import Depends, Header, HTTPException

from shared.application.user_auth.dto import IdentidadUsuarioAutenticada
from shared.application.user_auth.errors import TokenUsuarioInvalidoError
from shared.infrastructure.security.verificador_token_usuario_jwt import (
    VerificadorTokenUsuarioJWT,
)

_verificador = VerificadorTokenUsuarioJWT()


def requiere_usuario_autenticado(
    authorization: Annotated[str | None, Header()] = None,
) -> IdentidadUsuarioAutenticada:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token de autenticacion requerido.")

    token = authorization.removeprefix("Bearer ").strip()

    try:
        return _verificador.verificar(token)
    except TokenUsuarioInvalidoError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def requiere_rol(*roles_permitidos: str):
    def _verificar_rol(
        identidad: Annotated[
            IdentidadUsuarioAutenticada, Depends(requiere_usuario_autenticado)
        ],
    ) -> IdentidadUsuarioAutenticada:
        if identidad.rol not in roles_permitidos:
            raise HTTPException(status_code=403, detail="No tiene permisos para esta accion.")
        return identidad

    return _verificar_rol
