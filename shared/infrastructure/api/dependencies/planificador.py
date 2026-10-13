import logging
from typing import Annotated

from fastapi import Header, Request

from config.settings import settings
from shared.application.client_auth.errors import (
    EmailTokenNoDisponibleError,
    TokenInvalidoError,
)
from shared.application.user_auth.errors import PermisosInsuficientesError
from shared.infrastructure.api.dependencies.user_authentication import (
    requiere_usuario_autenticado,
)
from shared.infrastructure.gcp.authentication.token_verifier import (
    VerificadorTokenIdentidadGoogle,
)

logger = logging.getLogger(__name__)

_ROL_ADMINISTRADOR_GENERAL = "administrador_general"
_verificador: VerificadorTokenIdentidadGoogle | None = None


def _obtener_verificador() -> VerificadorTokenIdentidadGoogle:
    global _verificador
    if _verificador is None:
        _verificador = VerificadorTokenIdentidadGoogle(settings.GOOGLE_CLOUD_RUN_AUDIENCE)
    return _verificador


def _es_planificador_autorizado(authorization: str | None) -> bool:
    """Si la peticion trae el token de identidad de Google de la cuenta de servicio de Cloud Scheduler.

    El token lo firma Google y su audiencia es este servicio, pero cualquier cuenta de servicio de
    cualquier proyecto puede pedir uno con esa audiencia: por eso ademas se exige que el correo sea el de
    la cuenta autorizada (OWASP A01).
    """
    if not authorization or not authorization.startswith("Bearer "):
        return False

    if not settings.SCHEDULER_SERVICE_ACCOUNT_EMAIL or not settings.GOOGLE_CLOUD_RUN_AUDIENCE:
        return False

    try:
        identidad = _obtener_verificador().verificar(authorization.removeprefix("Bearer ").strip())
    except (TokenInvalidoError, EmailTokenNoDisponibleError):
        # No es un token de Google (puede ser el de un usuario): se prueba como sesion de usuario.
        return False

    autorizado = (
        identidad.claims.get("email_verified") is True
        and identidad.email.lower() == settings.SCHEDULER_SERVICE_ACCOUNT_EMAIL.lower()
    )
    if not autorizado:
        logger.warning("Token de Google de una cuenta no autorizada: %s", identidad.email)

    return autorizado


async def requiere_admin_o_planificador(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    """Deja pasar a la cuenta de servicio de Cloud Scheduler o a un administrador general con sesion."""
    if _es_planificador_autorizado(authorization):
        return

    identidad = await requiere_usuario_autenticado(request, authorization)
    if identidad.rol != _ROL_ADMINISTRADOR_GENERAL:
        raise PermisosInsuficientesError()
