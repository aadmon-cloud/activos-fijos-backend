import dataclasses
from datetime import UTC, datetime

import pytest

from modules.activos.domain.entities import (
    Activo,
    Complemento,
    EstadoCicloVida,
    TipoActivo,
)
from shared.domain.entities.audit import AuditPersona

_AUDIT = AuditPersona(id_persona="0", nombre="Sistema", fecha=datetime(2026, 1, 1, tzinfo=UTC))


def _crear_activo(**overrides) -> Activo:
    valores = dict(
        id="1",
        nombre="Laptop Dell",
        numero_inventario="INV-001",
        tipo=TipoActivo.ACTIVO_FIJO,
        marca=None,
        modelo=None,
        serie=None,
        descripcion=None,
        categoria_id="c1",
        area_id="a1",
        responsable_id="u1",
        condicion_id="cond1",
        estado_ciclo_vida=EstadoCicloVida.DISPONIBLE,
        sede_id="s1",
        lugar_id="l1",
        complementos=[],
        observaciones=None,
        foto_url=None,
        ficha_tecnica_url=None,
        creado_por=_AUDIT,
        actualizado_por=None,
    )
    valores.update(overrides)
    return Activo(**valores)


def test_activo_se_crea_con_los_campos_esperados():
    activo = _crear_activo()

    assert activo.nombre == "Laptop Dell"
    assert activo.estado_ciclo_vida == EstadoCicloVida.DISPONIBLE


def test_activo_es_inmutable():
    activo = _crear_activo()

    with pytest.raises(dataclasses.FrozenInstanceError):
        activo.nombre = "Otro"


def test_complemento_se_crea_con_los_campos_esperados():
    complemento = Complemento(nombre="Cargador", descripcion=None, cantidad=1, serie=None)

    assert complemento.nombre == "Cargador"
    assert complemento.cantidad == 1


def test_tipo_activo_tiene_los_dos_valores_esperados():
    assert {t.value for t in TipoActivo} == {"activo_fijo", "elemento"}


def test_estado_ciclo_vida_tiene_los_seis_valores_esperados():
    valores = {e.value for e in EstadoCicloVida}

    assert valores == {
        "disponible",
        "prestado",
        "en_mantenimiento",
        "dado_de_baja",
        "perdido",
        "danado",
    }
