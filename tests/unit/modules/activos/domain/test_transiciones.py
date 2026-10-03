import pytest

from modules.activos.domain.entities import EstadoCicloVida
from modules.activos.domain.transiciones import es_transicion_valida


@pytest.mark.parametrize(
    ("desde", "hacia"),
    [
        (EstadoCicloVida.DISPONIBLE, EstadoCicloVida.PRESTADO),
        (EstadoCicloVida.DISPONIBLE, EstadoCicloVida.DADO_DE_BAJA),
        (EstadoCicloVida.PRESTADO, EstadoCicloVida.DISPONIBLE),
        (EstadoCicloVida.EN_MANTENIMIENTO, EstadoCicloVida.DISPONIBLE),
        (EstadoCicloVida.DANADO, EstadoCicloVida.EN_MANTENIMIENTO),
        (EstadoCicloVida.PERDIDO, EstadoCicloVida.DISPONIBLE),
    ],
)
def test_transiciones_validas(desde, hacia):
    assert es_transicion_valida(desde, hacia) is True


@pytest.mark.parametrize(
    ("desde", "hacia"),
    [
        (EstadoCicloVida.DADO_DE_BAJA, EstadoCicloVida.DISPONIBLE),
        (EstadoCicloVida.PRESTADO, EstadoCicloVida.EN_MANTENIMIENTO),
        (EstadoCicloVida.EN_MANTENIMIENTO, EstadoCicloVida.PRESTADO),
        (EstadoCicloVida.DANADO, EstadoCicloVida.PRESTADO),
    ],
)
def test_transiciones_invalidas(desde, hacia):
    assert es_transicion_valida(desde, hacia) is False


def test_dado_de_baja_es_terminal():
    for estado in EstadoCicloVida:
        assert es_transicion_valida(EstadoCicloVida.DADO_DE_BAJA, estado) is False
