import pytest

from modules.solicitudes.domain.entities import EstadoSolicitud
from modules.solicitudes.domain.transiciones import es_transicion_valida


@pytest.mark.parametrize(
    ("desde", "hacia"),
    [
        (EstadoSolicitud.PENDIENTE, EstadoSolicitud.EN_PROCESO),
        (EstadoSolicitud.PENDIENTE, EstadoSolicitud.RECHAZADA),
        (EstadoSolicitud.EN_PROCESO, EstadoSolicitud.RESUELTA),
        (EstadoSolicitud.EN_PROCESO, EstadoSolicitud.RECHAZADA),
        (EstadoSolicitud.RESUELTA, EstadoSolicitud.CERRADA),
    ],
)
def test_transiciones_validas(desde, hacia):
    assert es_transicion_valida(desde, hacia) is True


@pytest.mark.parametrize(
    ("desde", "hacia"),
    [
        (EstadoSolicitud.PENDIENTE, EstadoSolicitud.RESUELTA),
        (EstadoSolicitud.PENDIENTE, EstadoSolicitud.CERRADA),
        (EstadoSolicitud.EN_PROCESO, EstadoSolicitud.PENDIENTE),
        (EstadoSolicitud.RESUELTA, EstadoSolicitud.EN_PROCESO),
        (EstadoSolicitud.CERRADA, EstadoSolicitud.PENDIENTE),
        (EstadoSolicitud.RECHAZADA, EstadoSolicitud.PENDIENTE),
    ],
)
def test_transiciones_invalidas(desde, hacia):
    assert es_transicion_valida(desde, hacia) is False
