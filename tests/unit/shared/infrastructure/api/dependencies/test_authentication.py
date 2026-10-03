from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from shared.application.client_auth.dto import IdentidadAutenticada
from shared.application.client_auth.errors import TokenInvalidoError
from shared.infrastructure.api.dependencies.authentication import autenticar_cliente


def test_autenticar_cliente_lanza_401_si_no_hay_header():
    with pytest.raises(HTTPException) as exc_info:
        autenticar_cliente(authorization=None)

    assert exc_info.value.status_code == 401


@patch("shared.infrastructure.api.dependencies.authentication._obtener_verificador")
def test_autenticar_cliente_retorna_identidad_si_el_token_es_valido(obtener_verificador_mock):
    verificador_falso = MagicMock()
    verificador_falso.verificar.return_value = IdentidadAutenticada(email="x@y.com")
    obtener_verificador_mock.return_value = verificador_falso

    identidad = autenticar_cliente(authorization="Bearer token-valido")

    assert identidad.email == "x@y.com"
    verificador_falso.verificar.assert_called_once_with("token-valido")


@patch("shared.infrastructure.api.dependencies.authentication._obtener_verificador")
def test_autenticar_cliente_lanza_401_si_el_token_es_invalido(obtener_verificador_mock):
    verificador_falso = MagicMock()
    verificador_falso.verificar.side_effect = TokenInvalidoError("expirado")
    obtener_verificador_mock.return_value = verificador_falso

    with pytest.raises(HTTPException) as exc_info:
        autenticar_cliente(authorization="Bearer token-invalido")

    assert exc_info.value.status_code == 401
