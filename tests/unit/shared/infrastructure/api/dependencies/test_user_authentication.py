from unittest.mock import patch

import pytest
from fastapi import HTTPException

from shared.application.user_auth.dto import IdentidadUsuarioAutenticada
from shared.application.user_auth.errors import TokenUsuarioInvalidoError
from shared.infrastructure.api.dependencies.user_authentication import (
    requiere_rol,
    requiere_usuario_autenticado,
)


def test_requiere_usuario_autenticado_lanza_401_si_no_hay_header():
    with pytest.raises(HTTPException) as exc_info:
        requiere_usuario_autenticado(authorization=None)

    assert exc_info.value.status_code == 401


@patch("shared.infrastructure.api.dependencies.user_authentication._verificador")
def test_requiere_usuario_autenticado_retorna_identidad_si_el_token_es_valido(
    verificador_mock,
):
    verificador_mock.verificar.return_value = IdentidadUsuarioAutenticada(
        id_usuario="1", email="a@b.com", nombre="Ana", rol="administrador_general"
    )

    identidad = requiere_usuario_autenticado(authorization="Bearer token-valido")

    assert identidad.email == "a@b.com"
    verificador_mock.verificar.assert_called_once_with("token-valido")


@patch("shared.infrastructure.api.dependencies.user_authentication._verificador")
def test_requiere_usuario_autenticado_lanza_401_si_el_token_es_invalido(verificador_mock):
    verificador_mock.verificar.side_effect = TokenUsuarioInvalidoError("expirado")

    with pytest.raises(HTTPException) as exc_info:
        requiere_usuario_autenticado(authorization="Bearer token-invalido")

    assert exc_info.value.status_code == 401


def test_requiere_rol_permite_el_acceso_si_el_rol_coincide():
    identidad = IdentidadUsuarioAutenticada(
        id_usuario="1", email="a@b.com", nombre="Ana", rol="administrador_general"
    )
    verificar_rol = requiere_rol("administrador_general")

    resultado = verificar_rol(identidad=identidad)

    assert resultado is identidad


def test_requiere_rol_lanza_403_si_el_rol_no_coincide():
    identidad = IdentidadUsuarioAutenticada(
        id_usuario="1", email="a@b.com", nombre="Ana", rol="empleado"
    )
    verificar_rol = requiere_rol("administrador_general")

    with pytest.raises(HTTPException) as exc_info:
        verificar_rol(identidad=identidad)

    assert exc_info.value.status_code == 403
