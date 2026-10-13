import asyncio
import hmac
import time

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from config.settings import settings
from modules.usuarios.application.ports.verificador_identidad_google import (
    IdentidadGoogle,
    VerificadorIdentidadGooglePort,
)
from modules.usuarios.domain.errors import (
    IngresoConGoogleNoConfiguradoError,
    TokenGoogleInvalidoError,
)

# Un token de ingreso se usa apenas Google lo entrega: pasados unos minutos se rechaza aunque siga vigente, para que
# uno que quedo en el historial del navegador no sirva para abrir una sesion.
EDAD_MAXIMA_TOKEN_SEGUNDOS = 300


class GoogleVerificadorIdentidad(VerificadorIdentidadGooglePort):
    """Valida el token de identidad (OpenID Connect) que Google entrega al navegador."""

    def __init__(self):
        self._request_adapter = google_requests.Request()

    async def verificar(self, credencial: str, nonce: str) -> IdentidadGoogle:
        client_id = settings.GOOGLE_CLIENT_ID
        if not client_id:
            raise IngresoConGoogleNoConfiguradoError()

        try:
            # La libreria comprueba firma, emisor, audiencia (nuestro ID de cliente) y vigencia. Usa red para
            # bajar las claves de Google, por eso va en otro hilo.
            info = await asyncio.to_thread(
                id_token.verify_oauth2_token, credencial, self._request_adapter, client_id
            )
        except Exception as exc:
            raise TokenGoogleInvalidoError() from exc

        email = info.get("email")
        if not isinstance(email, str) or not email.strip() or info.get("email_verified") is not True:
            raise TokenGoogleInvalidoError()

        emitido_en = info.get("iat")
        if not isinstance(emitido_en, int | float) or time.time() - emitido_en > EDAD_MAXIMA_TOKEN_SEGUNDOS:
            raise TokenGoogleInvalidoError()

        # El token debe haberse pedido para ESTE intento de ingreso (el nonce lo genera el navegador).
        nonce_del_token = info.get("nonce")
        if not nonce or not isinstance(nonce_del_token, str) or not hmac.compare_digest(nonce_del_token, nonce):
            raise TokenGoogleInvalidoError()

        return IdentidadGoogle(email=email.strip())
