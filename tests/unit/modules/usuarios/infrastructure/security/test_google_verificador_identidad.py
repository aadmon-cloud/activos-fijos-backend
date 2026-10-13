import time
from unittest.mock import patch

import pytest

from modules.usuarios.domain.errors import (
    IngresoConGoogleNoConfiguradoError,
    TokenGoogleInvalidoError,
)
from modules.usuarios.infrastructure.security import google_verificador_identidad as modulo
from modules.usuarios.infrastructure.security.google_verificador_identidad import (
    EDAD_MAXIMA_TOKEN_SEGUNDOS,
    GoogleVerificadorIdentidad,
)

_RUTA_SETTINGS = f"{modulo.__name__}.settings"
_RUTA_VERIFICAR = f"{modulo.__name__}.id_token.verify_oauth2_token"


def _info(**overrides):
    valores = {"email": "ana@fundacion.org", "email_verified": True, "iat": time.time(), "nonce": "nonce-1234"}
    valores.update(overrides)

    return valores


async def _verificar(info=None, client_id="client-id", nonce="nonce-1234", error=None):
    with patch(_RUTA_SETTINGS) as settings_mock, patch(_RUTA_VERIFICAR) as verificar_mock:
        settings_mock.GOOGLE_CLIENT_ID = client_id
        if error:
            verificar_mock.side_effect = error
        else:
            verificar_mock.return_value = info if info is not None else _info()

        resultado = await GoogleVerificadorIdentidad().verificar("token", nonce)

    return resultado, verificar_mock


async def test_un_token_valido_devuelve_el_correo_y_se_valida_contra_nuestro_id_de_cliente():
    resultado, verificar_mock = await _verificar()

    assert resultado.email == "ana@fundacion.org"
    assert verificar_mock.call_args.args[0] == "token"
    assert verificar_mock.call_args.args[2] == "client-id"


async def test_sin_id_de_cliente_configurado_falla_con_un_error_claro():
    with pytest.raises(IngresoConGoogleNoConfiguradoError):
        await _verificar(client_id=None)


async def test_un_token_que_la_libreria_rechaza_es_invalido():
    with pytest.raises(TokenGoogleInvalidoError):
        await _verificar(error=ValueError("firma invalida"))


@pytest.mark.parametrize(
    "cambios",
    [
        {"email_verified": False},
        {"email_verified": "true"},
        {"email": ""},
        {"email": None},
    ],
)
async def test_el_correo_debe_existir_y_estar_verificado_por_google(cambios):
    with pytest.raises(TokenGoogleInvalidoError):
        await _verificar(info=_info(**cambios))


async def test_un_token_viejo_se_rechaza_aunque_siga_vigente():
    viejo = _info(iat=time.time() - EDAD_MAXIMA_TOKEN_SEGUNDOS - 5)

    with pytest.raises(TokenGoogleInvalidoError):
        await _verificar(info=viejo)


async def test_un_token_sin_fecha_de_emision_se_rechaza():
    info = _info()
    del info["iat"]

    with pytest.raises(TokenGoogleInvalidoError):
        await _verificar(info=info)


@pytest.mark.parametrize(
    "nonce_enviado, nonce_del_token",
    [("otro-nonce", "nonce-1234"), ("", "nonce-1234"), ("nonce-1234", None)],
)
async def test_el_token_debe_corresponder_a_este_intento_de_ingreso(nonce_enviado, nonce_del_token):
    with pytest.raises(TokenGoogleInvalidoError):
        await _verificar(info=_info(nonce=nonce_del_token), nonce=nonce_enviado)
