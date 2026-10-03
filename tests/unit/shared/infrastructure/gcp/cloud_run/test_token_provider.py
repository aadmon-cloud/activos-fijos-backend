from unittest.mock import patch

from shared.infrastructure.gcp.cloud_run.token_provider import (
    ProveedorTokenCloudRunGoogle,
)


@patch("shared.infrastructure.gcp.cloud_run.token_provider.google.oauth2.id_token.fetch_id_token")
def test_obtener_token_delega_en_fetch_id_token(fetch_id_token_mock):
    fetch_id_token_mock.return_value = "token-falso"

    proveedor = ProveedorTokenCloudRunGoogle()
    token = proveedor.obtener_token("https://mi-servicio.example.com")

    assert token == "token-falso"
    fetch_id_token_mock.assert_called_once()
    assert fetch_id_token_mock.call_args.kwargs["audience"] == "https://mi-servicio.example.com"
