from typing import Annotated

from fastapi import Header, HTTPException

from config.settings import settings
from shared.application.client_auth.dto import IdentidadAutenticada
from shared.application.client_auth.errors import (
    EmailTokenNoDisponibleError,
    TokenInvalidoError,
)
from shared.infrastructure.gcp.authentication.token_verifier import (
    VerificadorTokenIdentidadGoogle,
)

_verificador: VerificadorTokenIdentidadGoogle | None = None


def _obtener_verificador() -> VerificadorTokenIdentidadGoogle:
    global _verificador
    if _verificador is None:
        if not settings.GOOGLE_CLOUD_RUN_AUDIENCE:
            raise RuntimeError(
                "GOOGLE_CLOUD_RUN_AUDIENCE debe estar configurado para autenticar clientes."
            )
        _verificador = VerificadorTokenIdentidadGoogle(settings.GOOGLE_CLOUD_RUN_AUDIENCE)
    return _verificador


def autenticar_cliente(
    authorization: Annotated[str | None, Header()] = None,
) -> IdentidadAutenticada:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token de autenticacion requerido.")

    token = authorization.removeprefix("Bearer ").strip()

    try:
        return _obtener_verificador().verificar(token)
    except (TokenInvalidoError, EmailTokenNoDisponibleError) as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
