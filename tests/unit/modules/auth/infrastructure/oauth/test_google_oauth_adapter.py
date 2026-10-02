from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from modules.auth.domain.errors import GoogleOAuthError, GoogleOAuthNoConfiguradoError
from modules.auth.infrastructure.oauth.google_oauth_adapter import GoogleOAuthAdapter


def _adapter(client_id="cid", client_secret="csecret", redirect_uri="http://x/callback"):
    return GoogleOAuthAdapter(client_id, client_secret, redirect_uri)


def _respuesta(json_data):
    respuesta = MagicMock()
    respuesta.json.return_value = json_data
    return respuesta


def _cliente_httpx_falso(respuestas_post, respuestas_get):
    cliente = MagicMock()
    cliente.post = AsyncMock(side_effect=respuestas_post)
    cliente.get = AsyncMock(side_effect=respuestas_get)
    contexto = MagicMock()
    contexto.__aenter__ = AsyncMock(return_value=cliente)
    contexto.__aexit__ = AsyncMock(return_value=False)
    return contexto


# construir_url_autorizacion


def test_construir_url_autorizacion_incluye_client_id_y_redirect_uri():
    url = _adapter(client_id="mi-client-id").construir_url_autorizacion()

    assert "client_id=mi-client-id" in url
    assert "response_type=code" in url


def test_construir_url_autorizacion_sin_configurar_lanza_error():
    with pytest.raises(GoogleOAuthNoConfiguradoError):
        _adapter(client_id="").construir_url_autorizacion()


# obtener_datos_usuario


async def test_obtener_datos_usuario_sin_configurar_lanza_error():
    with pytest.raises(GoogleOAuthNoConfiguradoError):
        await _adapter(client_secret="").obtener_datos_usuario("code-123")


async def test_obtener_datos_usuario_exitoso():
    contexto = _cliente_httpx_falso(
        respuestas_post=[_respuesta({"access_token": "tok-google"})],
        respuestas_get=[
            _respuesta(
                {
                    "email": "ana@gmail.com",
                    "id": "g-123",
                    "name": "Ana Perez",
                    "picture": "http://pic",
                }
            )
        ],
    )

    with patch(
        "modules.auth.infrastructure.oauth.google_oauth_adapter.httpx.AsyncClient",
        return_value=contexto,
    ):
        datos = await _adapter().obtener_datos_usuario("code-123")

    assert datos.email == "ana@gmail.com"
    assert datos.google_id == "g-123"
    assert datos.nombre == "Ana Perez"


async def test_obtener_datos_usuario_error_en_intercambio_lanza_google_oauth_error():
    contexto = _cliente_httpx_falso(
        respuestas_post=[_respuesta({"error": "invalid_grant"})],
        respuestas_get=[],
    )

    with patch(
        "modules.auth.infrastructure.oauth.google_oauth_adapter.httpx.AsyncClient",
        return_value=contexto,
    ):
        with pytest.raises(GoogleOAuthError):
            await _adapter().obtener_datos_usuario("code-invalido")


async def test_obtener_datos_usuario_sin_email_lanza_google_oauth_error():
    contexto = _cliente_httpx_falso(
        respuestas_post=[_respuesta({"access_token": "tok-google"})],
        respuestas_get=[_respuesta({"id": "g-123"})],
    )

    with patch(
        "modules.auth.infrastructure.oauth.google_oauth_adapter.httpx.AsyncClient",
        return_value=contexto,
    ):
        with pytest.raises(GoogleOAuthError):
            await _adapter().obtener_datos_usuario("code-123")
