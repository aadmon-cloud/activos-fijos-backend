from unittest.mock import MagicMock

from modules.auth.application.services.iniciar_login_google import (
    IniciarLoginGoogleService,
)


def test_ejecutar_retorna_la_url_del_puerto():
    google_oauth_mock = MagicMock()
    google_oauth_mock.construir_url_autorizacion.return_value = "https://accounts.google.com/x"

    service = IniciarLoginGoogleService(google_oauth_mock)

    assert service.ejecutar() == "https://accounts.google.com/x"
    google_oauth_mock.construir_url_autorizacion.assert_called_once()
