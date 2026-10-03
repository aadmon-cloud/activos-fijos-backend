from unittest.mock import MagicMock

import pytest

from shared.application.service_invocation.dto import (
    ConfiguracionServicioExterno,
    SolicitudServicioExterno,
)
from shared.application.service_invocation.exceptions import (
    ErrorInvocacionServicioExterno,
)
from shared.infrastructure.gcp.cloud_run.client import ClienteCloudRun


class _ResolutorFalso:
    def __init__(self, configuracion: ConfiguracionServicioExterno):
        self._configuracion = configuracion

    def resolver(self, nombre_servicio: str) -> ConfiguracionServicioExterno:
        return self._configuracion


class _ProveedorTokenFalso:
    def obtener_token(self, audiencia: str) -> str:
        return "token-de-prueba"


def _respuesta_falsa(status_code=200, json_data=None, ok=True):
    respuesta = MagicMock()
    respuesta.ok = ok
    respuesta.status_code = status_code
    respuesta.content = b"{}"
    respuesta.headers = {"Content-Type": "application/json"}
    respuesta.json.return_value = json_data or {}
    return respuesta


def test_invocar_agrega_bearer_token_cuando_requiere_autenticacion():
    sesion_falsa = MagicMock()
    sesion_falsa.request.return_value = _respuesta_falsa(json_data={"ok": True})

    configuracion = ConfiguracionServicioExterno(
        nombre="facturacion",
        url_base="https://facturacion.example.com",
        audiencia_resuelta="https://facturacion.example.com",
        requiere_autenticacion=True,
    )
    cliente = ClienteCloudRun(
        resolutor=_ResolutorFalso(configuracion),
        proveedor_token=_ProveedorTokenFalso(),
        sesion=sesion_falsa,
    )

    resultado = cliente.invocar("facturacion", SolicitudServicioExterno(ruta="/api/facturas"))

    assert resultado == {"ok": True}
    cabeceras_enviadas = sesion_falsa.request.call_args.kwargs["headers"]
    assert cabeceras_enviadas["Authorization"] == "Bearer token-de-prueba"


def test_invocar_lanza_error_propio_si_la_respuesta_no_es_ok():
    sesion_falsa = MagicMock()
    sesion_falsa.request.return_value = _respuesta_falsa(status_code=500, ok=False)

    configuracion = ConfiguracionServicioExterno(
        nombre="facturacion",
        url_base="https://facturacion.example.com",
        requiere_autenticacion=False,
    )
    cliente = ClienteCloudRun(
        resolutor=_ResolutorFalso(configuracion),
        proveedor_token=_ProveedorTokenFalso(),
        sesion=sesion_falsa,
    )

    with pytest.raises(ErrorInvocacionServicioExterno):
        cliente.invocar("facturacion", SolicitudServicioExterno(ruta="/api/facturas"))
