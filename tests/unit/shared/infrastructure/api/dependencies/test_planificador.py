from unittest.mock import MagicMock, patch

import pytest
from starlette.requests import Request

from shared.application.client_auth.dto import IdentidadAutenticada
from shared.application.client_auth.errors import TokenInvalidoError
from shared.application.user_auth.dto import IdentidadUsuarioAutenticada
from shared.application.user_auth.errors import PermisosInsuficientesError
from shared.infrastructure.api.dependencies import planificador

_RUTA = "shared.infrastructure.api.dependencies.planificador"
_CUENTA = "planificador@proyecto.iam.gserviceaccount.com"


def _settings(**overrides):
    mock = MagicMock()
    mock.SCHEDULER_SERVICE_ACCOUNT_EMAIL = _CUENTA
    mock.GOOGLE_CLOUD_RUN_AUDIENCE = "https://servicio.run.app"
    for clave, valor in overrides.items():
        setattr(mock, clave, valor)
    return mock


def _verificador(identidad=None, error=None):
    mock = MagicMock()
    if error:
        mock.verificar.side_effect = error
    else:
        mock.verificar.return_value = identidad
    return mock


def _token_google(email=_CUENTA, verificado=True):
    return IdentidadAutenticada(email=email, claims={"email_verified": verificado})


def test_acepta_el_token_de_la_cuenta_de_servicio_autorizada():
    with patch(f"{_RUTA}.settings", _settings()), patch(
        f"{_RUTA}._obtener_verificador", return_value=_verificador(_token_google())
    ):
        assert planificador._es_planificador_autorizado("Bearer token") is True


def test_la_comparacion_del_correo_no_distingue_mayusculas():
    with patch(f"{_RUTA}.settings", _settings()), patch(
        f"{_RUTA}._obtener_verificador", return_value=_verificador(_token_google(_CUENTA.upper()))
    ):
        assert planificador._es_planificador_autorizado("Bearer token") is True


def test_rechaza_un_token_valido_de_otra_cuenta_de_servicio():
    with patch(f"{_RUTA}.settings", _settings()), patch(
        f"{_RUTA}._obtener_verificador", return_value=_verificador(_token_google("otra@otro.iam.gserviceaccount.com"))
    ):
        assert planificador._es_planificador_autorizado("Bearer token") is False


def test_rechaza_un_correo_no_verificado():
    with patch(f"{_RUTA}.settings", _settings()), patch(
        f"{_RUTA}._obtener_verificador", return_value=_verificador(_token_google(verificado=False))
    ):
        assert planificador._es_planificador_autorizado("Bearer token") is False


def test_un_token_que_no_es_de_google_no_es_del_planificador():
    with patch(f"{_RUTA}.settings", _settings()), patch(
        f"{_RUTA}._obtener_verificador", return_value=_verificador(error=TokenInvalidoError("x"))
    ):
        assert planificador._es_planificador_autorizado("Bearer jwt-de-usuario") is False


@pytest.mark.parametrize("authorization", [None, "", "Basic abc"])
def test_sin_bearer_no_es_del_planificador(authorization):
    with patch(f"{_RUTA}.settings", _settings()):
        assert planificador._es_planificador_autorizado(authorization) is False


@pytest.mark.parametrize("ajuste", [{"SCHEDULER_SERVICE_ACCOUNT_EMAIL": None}, {"GOOGLE_CLOUD_RUN_AUDIENCE": None}])
def test_sin_la_cuenta_o_la_audiencia_configuradas_nadie_entra_como_planificador(ajuste):
    verificador = _verificador(_token_google())

    with patch(f"{_RUTA}.settings", _settings(**ajuste)), patch(f"{_RUTA}._obtener_verificador", return_value=verificador):
        assert planificador._es_planificador_autorizado("Bearer token") is False

    verificador.verificar.assert_not_called()


def _request():
    return Request({"type": "http", "headers": [], "method": "POST", "path": "/"})


async def test_el_planificador_autorizado_pasa_sin_sesion_de_usuario():
    with patch(f"{_RUTA}._es_planificador_autorizado", return_value=True), patch(
        f"{_RUTA}.requiere_usuario_autenticado"
    ) as sesion:
        await planificador.requiere_admin_o_planificador(_request(), "Bearer token")

    sesion.assert_not_called()


async def test_un_administrador_con_sesion_pasa():
    identidad = IdentidadUsuarioAutenticada(
        id_usuario="1", email="a@x.com", nombre="Admin", rol="administrador_general", area_id=None
    )

    async def sesion(request, authorization):
        return identidad

    with patch(f"{_RUTA}._es_planificador_autorizado", return_value=False), patch(
        f"{_RUTA}.requiere_usuario_autenticado", sesion
    ):
        await planificador.requiere_admin_o_planificador(_request(), None)


async def test_un_usuario_que_no_es_administrador_recibe_permisos_insuficientes():
    identidad = IdentidadUsuarioAutenticada(
        id_usuario="2", email="b@x.com", nombre="Emp", rol="empleado", area_id=None
    )

    async def sesion(request, authorization):
        return identidad

    with patch(f"{_RUTA}._es_planificador_autorizado", return_value=False), patch(
        f"{_RUTA}.requiere_usuario_autenticado", sesion
    ), pytest.raises(PermisosInsuficientesError):
        await planificador.requiere_admin_o_planificador(_request(), None)
