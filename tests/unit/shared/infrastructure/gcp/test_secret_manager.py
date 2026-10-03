from unittest.mock import MagicMock, patch

import pytest
from google.api_core.exceptions import NotFound, PermissionDenied

from shared.infrastructure.gcp.secret_manager import (
    ErrorRecuperacionSecreto,
    GestorSecretosGCP,
)


def _respuesta_falsa(valor: str) -> MagicMock:
    respuesta = MagicMock()
    respuesta.payload.data.decode.return_value = valor
    return respuesta


@patch("shared.infrastructure.gcp.secret_manager.secretmanager.SecretManagerServiceClient")
def test_obtener_secreto_retorna_el_valor_decodificado(cliente_mock_cls):
    cliente_mock_cls.return_value.access_secret_version.return_value = _respuesta_falsa("valor-secreto")

    gestor = GestorSecretosGCP("mi-proyecto")
    valor = gestor.obtener_secreto("mi-secreto")

    assert valor == "valor-secreto"


@patch("shared.infrastructure.gcp.secret_manager.secretmanager.SecretManagerServiceClient")
def test_obtener_secreto_lanza_error_propio_si_no_existe(cliente_mock_cls):
    cliente_mock_cls.return_value.access_secret_version.side_effect = NotFound("no existe")

    gestor = GestorSecretosGCP("mi-proyecto")

    with pytest.raises(ErrorRecuperacionSecreto):
        gestor.obtener_secreto("no-existe")


@patch("shared.infrastructure.gcp.secret_manager.secretmanager.SecretManagerServiceClient")
def test_obtener_secreto_lanza_error_propio_si_no_hay_permisos(cliente_mock_cls):
    cliente_mock_cls.return_value.access_secret_version.side_effect = PermissionDenied("sin permiso")

    gestor = GestorSecretosGCP("mi-proyecto")

    with pytest.raises(ErrorRecuperacionSecreto):
        gestor.obtener_secreto("sin-permiso")
