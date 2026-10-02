from urllib.parse import urlencode

import httpx

from modules.auth.application.dto.datos_google_usuario_dto import DatosGoogleUsuarioDTO
from modules.auth.application.ports.google_oauth import GoogleOAuthPort
from modules.auth.domain.errors import GoogleOAuthError, GoogleOAuthNoConfiguradoError

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


class GoogleOAuthAdapter(GoogleOAuthPort):
    """Intercambio manual código→token→userinfo vía httpx.

    Este es el flujo confirmado como el que realmente funciona en el legacy
    (ver MIGRATION_PLAN.md, módulo auth): la integración registrada con
    `authlib` en el legacy nunca se invocaba.
    """

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri

    def construir_url_autorizacion(self) -> str:
        if not self._client_id or not self._redirect_uri:
            raise GoogleOAuthNoConfiguradoError()

        parametros = {
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"{AUTH_URL}?{urlencode(parametros)}"

    async def obtener_datos_usuario(self, code: str) -> DatosGoogleUsuarioDTO:
        if not self._client_id or not self._client_secret or not self._redirect_uri:
            raise GoogleOAuthNoConfiguradoError()

        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                TOKEN_URL,
                data={
                    "code": code,
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "redirect_uri": self._redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            token_data = token_response.json()

            if "error" in token_data:
                raise GoogleOAuthError(
                    token_data.get("error_description", token_data["error"])
                )

            access_token = token_data.get("access_token")
            userinfo_response = await client.get(
                USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"}
            )
            user_info = userinfo_response.json()

        email = user_info.get("email")
        if not email:
            raise GoogleOAuthError("Google no retornó un email.")

        return DatosGoogleUsuarioDTO(
            email=email,
            google_id=user_info.get("id", ""),
            nombre=user_info.get("name", email.split("@")[0]),
            picture=user_info.get("picture"),
        )
