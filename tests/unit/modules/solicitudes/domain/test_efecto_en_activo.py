import pytest

from modules.solicitudes.domain.efecto_en_activo import (
    ETIQUETAS_ESTADO_ACTIVO,
    EfectoEnActivo,
    efecto_en_activo,
)
from modules.solicitudes.domain.entities import EstadoSolicitud, TipoSolicitud


@pytest.mark.parametrize(
    "tipo, estado, esperado",
    [
        (TipoSolicitud.MANTENIMIENTO, EstadoSolicitud.EN_PROCESO, EfectoEnActivo("en_mantenimiento")),
        (
            TipoSolicitud.MANTENIMIENTO,
            EstadoSolicitud.RESUELTA,
            EfectoEnActivo("disponible", solo_si_actual="en_mantenimiento"),
        ),
        (TipoSolicitud.REPORTE_DANO, EstadoSolicitud.EN_PROCESO, EfectoEnActivo("danado")),
        (TipoSolicitud.REPORTE_PERDIDA, EstadoSolicitud.EN_PROCESO, EfectoEnActivo("perdido")),
    ],
)
def test_efectos_definidos(tipo, estado, esperado):
    assert efecto_en_activo(tipo, estado) == esperado


@pytest.mark.parametrize(
    "tipo, estado",
    [
        (TipoSolicitud.MANTENIMIENTO, EstadoSolicitud.RECHAZADA),
        (TipoSolicitud.MANTENIMIENTO, EstadoSolicitud.CERRADA),
        (TipoSolicitud.REPORTE_DANO, EstadoSolicitud.RESUELTA),
        (TipoSolicitud.REPORTE_PERDIDA, EstadoSolicitud.RECHAZADA),
        (TipoSolicitud.CAMBIO, EstadoSolicitud.EN_PROCESO),
        (TipoSolicitud.AJUSTE, EstadoSolicitud.RESUELTA),
    ],
)
def test_sin_efecto_cuando_la_regla_no_lo_pide(tipo, estado):
    assert efecto_en_activo(tipo, estado) is None


def test_los_estados_destino_tienen_etiqueta():
    for tipo in TipoSolicitud:
        for estado in EstadoSolicitud:
            efecto = efecto_en_activo(tipo, estado)
            if efecto:
                assert efecto.estado_destino in ETIQUETAS_ESTADO_ACTIVO
