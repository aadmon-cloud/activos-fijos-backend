import dataclasses
from datetime import UTC, datetime

import pytest

from modules.solicitudes.domain.entities import (
    EntradaSeguimiento,
    EstadoSolicitud,
    PrioridadSolicitud,
    Solicitud,
    TipoSolicitud,
)
from shared.domain.entities.audit import AuditPersona

_AUDIT = AuditPersona(id_persona="0", nombre="Sistema", fecha=datetime(2026, 1, 1, tzinfo=UTC))


def _crear_solicitud(**overrides) -> Solicitud:
    valores = dict(
        id="1",
        tipo=TipoSolicitud.MANTENIMIENTO,
        activo_id="a1",
        descripcion="El equipo hace ruido",
        prioridad=PrioridadSolicitud.MEDIA,
        evidencias=[],
        estado=EstadoSolicitud.PENDIENTE,
        rol_asignado="mantenimiento",
        area_id=None,
        seguimiento=[],
        creado_por=_AUDIT,
        actualizado_por=None,
    )
    valores.update(overrides)
    return Solicitud(**valores)


def test_solicitud_se_crea_con_los_campos_esperados():
    solicitud = _crear_solicitud()

    assert solicitud.tipo == TipoSolicitud.MANTENIMIENTO
    assert solicitud.estado == EstadoSolicitud.PENDIENTE


def test_solicitud_es_inmutable():
    solicitud = _crear_solicitud()

    with pytest.raises(dataclasses.FrozenInstanceError):
        solicitud.descripcion = "Otra cosa"


def test_tipo_solicitud_tiene_los_cinco_valores_esperados():
    valores = {t.value for t in TipoSolicitud}

    assert valores == {"mantenimiento", "cambio", "ajuste", "reporte_dano", "reporte_perdida"}


def test_prioridad_solicitud_tiene_los_cuatro_valores_esperados():
    assert {p.value for p in PrioridadSolicitud} == {"baja", "media", "alta", "urgente"}


def test_estado_solicitud_tiene_los_cinco_valores_esperados():
    valores = {e.value for e in EstadoSolicitud}

    assert valores == {"pendiente", "en_proceso", "resuelta", "cerrada", "rechazada"}


def test_entrada_seguimiento_se_crea_con_los_campos_esperados():
    entrada = EntradaSeguimiento(
        autor=_AUDIT, comentario="Visto", estado_anterior=None, estado_nuevo=None
    )

    assert entrada.comentario == "Visto"
