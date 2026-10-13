import dataclasses
from datetime import UTC, datetime

import pytest

from modules.mantenimientos.domain.entities import (
    ArchivoMantenimiento,
    EstadoMantenimiento,
    Mantenimiento,
    TipoMantenimiento,
)
from shared.domain.entities.audit import AuditPersona

_AUDIT = AuditPersona(id_persona="0", nombre="Sistema", fecha=datetime(2026, 1, 1, tzinfo=UTC))


def _crear_mantenimiento(**overrides) -> Mantenimiento:
    valores = dict(
        id="1",
        activo_id="a1",
        solicitud_id=None,
        tipo=TipoMantenimiento.PREVENTIVO,
        tecnico_responsable_id="u1",
        fecha=datetime(2026, 1, 1, tzinfo=UTC),
        observaciones=None,
        costo=None,
        documentos=[],
        evidencias=[],
        estado=EstadoMantenimiento.PROGRAMADO,
        frecuencia_dias=None,
        proxima_fecha_sugerida=None,
        alerta_enviada=False,
        creado_por=_AUDIT,
        actualizado_por=None,
    )
    valores.update(overrides)
    return Mantenimiento(**valores)


def test_mantenimiento_se_crea_con_los_campos_esperados():
    mantenimiento = _crear_mantenimiento()

    assert mantenimiento.tipo == TipoMantenimiento.PREVENTIVO
    assert mantenimiento.estado == EstadoMantenimiento.PROGRAMADO


def test_mantenimiento_es_inmutable():
    mantenimiento = _crear_mantenimiento()

    with pytest.raises(dataclasses.FrozenInstanceError):
        mantenimiento.observaciones = "otra cosa"


def test_archivo_mantenimiento_se_crea_con_los_campos_esperados():
    archivo = ArchivoMantenimiento(archivo_id="f1", nombre="foto.jpg")

    assert archivo.archivo_id == "f1"
    assert archivo.nombre == "foto.jpg"


def test_tipo_mantenimiento_tiene_los_tres_valores_esperados():
    assert {t.value for t in TipoMantenimiento} == {"preventivo", "correctivo", "locativo"}


def test_estado_mantenimiento_tiene_los_cuatro_valores_esperados():
    valores = {e.value for e in EstadoMantenimiento}

    assert valores == {"programado", "en_proceso", "completado", "cancelado"}
