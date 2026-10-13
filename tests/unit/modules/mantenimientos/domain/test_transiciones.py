import pytest

from modules.mantenimientos.domain.entities import EstadoMantenimiento
from modules.mantenimientos.domain.transiciones import es_transicion_valida, estados_destino


@pytest.mark.parametrize(
    ("desde", "hacia"),
    [
        (EstadoMantenimiento.PROGRAMADO, EstadoMantenimiento.EN_PROCESO),
        (EstadoMantenimiento.PROGRAMADO, EstadoMantenimiento.CANCELADO),
        (EstadoMantenimiento.EN_PROCESO, EstadoMantenimiento.COMPLETADO),
        (EstadoMantenimiento.EN_PROCESO, EstadoMantenimiento.CANCELADO),
    ],
)
def test_transiciones_validas(desde, hacia):
    assert es_transicion_valida(desde, hacia) is True


@pytest.mark.parametrize(
    ("desde", "hacia"),
    [
        (EstadoMantenimiento.PROGRAMADO, EstadoMantenimiento.COMPLETADO),
        (EstadoMantenimiento.EN_PROCESO, EstadoMantenimiento.PROGRAMADO),
        (EstadoMantenimiento.COMPLETADO, EstadoMantenimiento.EN_PROCESO),
        (EstadoMantenimiento.CANCELADO, EstadoMantenimiento.PROGRAMADO),
    ],
)
def test_transiciones_invalidas(desde, hacia):
    assert es_transicion_valida(desde, hacia) is False


@pytest.mark.parametrize(
    ("desde", "esperados"),
    [
        (EstadoMantenimiento.PROGRAMADO, [EstadoMantenimiento.EN_PROCESO, EstadoMantenimiento.CANCELADO]),
        (EstadoMantenimiento.EN_PROCESO, [EstadoMantenimiento.COMPLETADO, EstadoMantenimiento.CANCELADO]),
        (EstadoMantenimiento.COMPLETADO, []),
        (EstadoMantenimiento.CANCELADO, []),
    ],
)
def test_estados_destino_en_el_orden_del_ciclo_de_vida(desde, esperados):
    assert estados_destino(desde) == esperados
