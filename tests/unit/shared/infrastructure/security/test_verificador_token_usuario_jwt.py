from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt

from config.settings import settings
from shared.application.user_auth.errors import TokenUsuarioInvalidoError
from shared.infrastructure.security.verificador_token_usuario_jwt import (
    VerificadorTokenUsuarioJWT,
)


def _generar_token(**overrides) -> str:
    payload = {
        "sub": "1",
        "email": "ana@example.com",
        "nombre": "Ana Garcia",
        "rol": "administrador_general",
        "exp": datetime.now(UTC) + timedelta(minutes=5),
    }
    payload.update(overrides)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def test_verificar_retorna_identidad_si_el_token_es_valido():
    token = _generar_token()
    verificador = VerificadorTokenUsuarioJWT()

    identidad = verificador.verificar(token)

    assert identidad.id_usuario == "1"
    assert identidad.email == "ana@example.com"
    assert identidad.nombre == "Ana Garcia"
    assert identidad.rol == "administrador_general"


def test_verificar_incluye_area_id_si_viene_en_el_token():
    token = _generar_token(area_id="area-1")
    verificador = VerificadorTokenUsuarioJWT()

    identidad = verificador.verificar(token)

    assert identidad.area_id == "area-1"


def test_verificar_deja_area_id_en_none_si_no_viene_en_el_token():
    token = _generar_token()
    verificador = VerificadorTokenUsuarioJWT()

    identidad = verificador.verificar(token)

    assert identidad.area_id is None


def test_verificar_lanza_error_si_el_token_esta_expirado():
    token = _generar_token(exp=datetime.now(UTC) - timedelta(minutes=1))
    verificador = VerificadorTokenUsuarioJWT()

    with pytest.raises(TokenUsuarioInvalidoError):
        verificador.verificar(token)


def test_verificar_lanza_error_si_faltan_claims_obligatorios():
    token = jwt.encode(
        {"sub": "1", "exp": datetime.now(UTC) + timedelta(minutes=5)},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    verificador = VerificadorTokenUsuarioJWT()

    with pytest.raises(TokenUsuarioInvalidoError):
        verificador.verificar(token)


def test_verificar_lanza_error_si_la_firma_es_invalida():
    token_con_otra_firma = jwt.encode(
        {
            "sub": "1",
            "email": "a@b.com",
            "nombre": "A",
            "rol": "empleado",
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        "otro-secreto-distinto",
        algorithm=settings.JWT_ALGORITHM,
    )
    verificador = VerificadorTokenUsuarioJWT()

    with pytest.raises(TokenUsuarioInvalidoError):
        verificador.verificar(token_con_otra_firma)
