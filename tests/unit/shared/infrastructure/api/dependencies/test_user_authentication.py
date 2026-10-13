from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.application.user_auth.dto import EstadoUsuario, IdentidadUsuarioAutenticada
from shared.application.user_auth.errors import (
    PermisosInsuficientesError,
    SesionInvalidaError,
    SesionRequeridaError,
    TokenUsuarioInvalidoError,
)
from shared.infrastructure.api.dependencies.user_authentication import (
    requiere_rol,
    requiere_usuario_autenticado,
)

_MODULO = "shared.infrastructure.api.dependencies.user_authentication"
_IDENTIDAD = IdentidadUsuarioAutenticada(
    id_usuario="1", email="a@b.com", nombre="Ana", rol="administrador_general"
)


def _request(cookies: dict[str, str] | None = None) -> MagicMock:
    request = MagicMock()
    request.cookies = cookies or {}
    return request


def _con_usuario(estado: EstadoUsuario | None):
    verificador = patch(f"{_MODULO}._verificador")
    consulta = patch(f"{_MODULO}._consulta_estado")
    verificador_mock = verificador.start()
    consulta_mock = consulta.start()
    verificador_mock.verificar.return_value = _IDENTIDAD
    consulta_mock.obtener = AsyncMock(return_value=estado)

    return verificador_mock, consulta_mock, (verificador, consulta)


@pytest.fixture
def estado_activo():
    verificador_mock, consulta_mock, patches = _con_usuario(
        EstadoUsuario(activo=True, rol="administrador_general")
    )
    yield verificador_mock, consulta_mock
    for p in patches:
        p.stop()


async def test_lanza_sesion_requerida_si_no_hay_cookie_ni_header():
    with pytest.raises(SesionRequeridaError) as exc_info:
        await requiere_usuario_autenticado(request=_request(), authorization=None)

    assert exc_info.value.code == "AUTH-001"


async def test_retorna_identidad_si_el_token_de_la_cookie_es_valido(estado_activo):
    verificador_mock, _ = estado_activo

    identidad = await requiere_usuario_autenticado(
        request=_request({"access_token": "token-cookie"}), authorization=None
    )

    assert identidad.email == "a@b.com"
    verificador_mock.verificar.assert_called_once_with("token-cookie")


async def test_acepta_bearer_como_alternativa_si_no_hay_cookie(estado_activo):
    verificador_mock, _ = estado_activo

    await requiere_usuario_autenticado(request=_request(), authorization="Bearer token-header")

    verificador_mock.verificar.assert_called_once_with("token-header")


async def test_la_cookie_tiene_prioridad_sobre_el_header(estado_activo):
    verificador_mock, _ = estado_activo

    await requiere_usuario_autenticado(
        request=_request({"access_token": "token-cookie"}), authorization="Bearer token-header"
    )

    verificador_mock.verificar.assert_called_once_with("token-cookie")


async def test_lanza_sesion_invalida_si_el_token_no_es_valido():
    with patch(f"{_MODULO}._verificador") as verificador_mock:
        verificador_mock.verificar.side_effect = TokenUsuarioInvalidoError("expirado")

        with pytest.raises(SesionInvalidaError) as exc_info:
            await requiere_usuario_autenticado(
                request=_request({"access_token": "malo"}), authorization=None
            )

    assert exc_info.value.code == "AUTH-002"


async def test_rechaza_con_sesion_invalida_a_un_usuario_desactivado():
    _, _, patches = _con_usuario(EstadoUsuario(activo=False, rol="administrador_general"))
    try:
        with pytest.raises(SesionInvalidaError):
            await requiere_usuario_autenticado(
                request=_request({"access_token": "t"}), authorization=None
            )
    finally:
        for p in patches:
            p.stop()


async def test_rechaza_con_sesion_invalida_a_un_usuario_que_ya_no_existe():
    _, _, patches = _con_usuario(None)
    try:
        with pytest.raises(SesionInvalidaError):
            await requiere_usuario_autenticado(
                request=_request({"access_token": "t"}), authorization=None
            )
    finally:
        for p in patches:
            p.stop()


async def test_usa_el_rol_actual_de_la_base_de_datos_y_no_el_del_token():
    _, _, patches = _con_usuario(EstadoUsuario(activo=True, rol="empleado"))
    try:
        identidad = await requiere_usuario_autenticado(
            request=_request({"access_token": "t"}), authorization=None
        )
    finally:
        for p in patches:
            p.stop()

    assert identidad.rol == "empleado"
    assert identidad.email == "a@b.com"


async def test_usa_el_area_actual_de_la_base_de_datos_y_no_la_del_token():
    _, _, patches = _con_usuario(EstadoUsuario(activo=True, rol="empleado", area_id="area-nueva"))
    try:
        identidad = await requiere_usuario_autenticado(
            request=_request({"access_token": "t"}), authorization=None
        )
    finally:
        for p in patches:
            p.stop()

    assert identidad.area_id == "area-nueva"


def test_requiere_rol_permite_el_acceso_si_el_rol_coincide():
    verificar_rol = requiere_rol("administrador_general")

    assert verificar_rol(identidad=_IDENTIDAD) is _IDENTIDAD


def test_requiere_rol_lanza_permisos_insuficientes_si_el_rol_no_coincide():
    identidad = IdentidadUsuarioAutenticada(
        id_usuario="1", email="a@b.com", nombre="Ana", rol="empleado"
    )
    verificar_rol = requiere_rol("administrador_general")

    with pytest.raises(PermisosInsuficientesError) as exc_info:
        verificar_rol(identidad=identidad)

    assert exc_info.value.code == "AUTH-003"
