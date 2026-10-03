from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from shared.application.client_auth.dto import IdentidadAutenticada
from shared.application.client_auth.errors import (
    EmailTokenNoDisponibleError,
    TokenInvalidoError,
)
from shared.application.client_auth.ports import VerificadorTokenIdentidadPort


class VerificadorTokenIdentidadGoogle(VerificadorTokenIdentidadPort):
    """Verifica tokens de identidad emitidos por Google."""

    def __init__(self, audiencia: str):
        self._audiencia = audiencia
        self._request_adapter = google_requests.Request()

    def verificar(self, token: str) -> IdentidadAutenticada:
        try:
            info = id_token.verify_oauth2_token(
                token,
                self._request_adapter,
                self._audiencia,
            )
        except Exception as exc:
            raise TokenInvalidoError(detalle=str(exc)) from exc

        email = info.get("email")
        if not isinstance(email, str) or not email.strip():
            raise EmailTokenNoDisponibleError()

        return IdentidadAutenticada(email=email.strip(), claims=dict(info))
