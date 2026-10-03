from unittest.mock import patch

import pytest

from shared.application.client_auth.errors import (
    EmailTokenNoDisponibleError,
    TokenInvalidoError,
)
from shared.infrastructure.gcp.authentication.token_verifier import (
    VerificadorTokenIdentidadGoogle,
)


@patch("shared.infrastructure.gcp.authentication.token_verifier.id_token.verify_oauth2_token")
def test_verificar_retorna_identidad_autenticada(verify_mock):
    verify_mock.return_value = {"email": "servicio@proyecto.iam.gserviceaccount.com"}

    verificador = VerificadorTokenIdentidadGoogle("https://mi-servicio.example.com")
    identidad = verificador.verificar("token-valido")

    assert identidad.email == "servicio@proyecto.iam.gserviceaccount.com"


@patch("shared.infrastructure.gcp.authentication.token_verifier.id_token.verify_oauth2_token")
def test_verificar_lanza_token_invalido_si_falla_la_verificacion(verify_mock):
    verify_mock.side_effect = ValueError("token expirado")

    verificador = VerificadorTokenIdentidadGoogle("https://mi-servicio.example.com")

    with pytest.raises(TokenInvalidoError):
        verificador.verificar("token-expirado")


@patch("shared.infrastructure.gcp.authentication.token_verifier.id_token.verify_oauth2_token")
def test_verificar_lanza_error_si_no_hay_email_en_el_token(verify_mock):
    verify_mock.return_value = {"sub": "12345"}

    verificador = VerificadorTokenIdentidadGoogle("https://mi-servicio.example.com")

    with pytest.raises(EmailTokenNoDisponibleError):
        verificador.verificar("token-sin-email")
