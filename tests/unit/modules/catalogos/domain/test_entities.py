import dataclasses
from datetime import UTC, datetime

import pytest

from modules.catalogos.domain.entities import Area, Categoria, Condicion, Lugar, Sede, TipoLugar
from shared.domain.entities.audit import AuditPersona

_AUDIT = AuditPersona(id_persona="0", nombre="Sistema", fecha=datetime(2026, 1, 1, tzinfo=UTC))


def test_area_se_crea_con_los_campos_esperados():
    area = Area(id="1", nombre="Direccion", descripcion=None, creado_por=_AUDIT, actualizado_por=None)

    assert area.id == "1"
    assert area.nombre == "Direccion"


def test_area_es_inmutable():
    area = Area(id="1", nombre="Direccion", descripcion=None, creado_por=_AUDIT, actualizado_por=None)

    with pytest.raises(dataclasses.FrozenInstanceError):
        area.nombre = "Otra"


def test_categoria_se_crea_con_los_campos_esperados():
    categoria = Categoria(
        id="1", nombre="Muebles", descripcion=None, creado_por=_AUDIT, actualizado_por=None
    )

    assert categoria.nombre == "Muebles"


def test_condicion_se_crea_con_los_campos_esperados():
    condicion = Condicion(
        id="1",
        nombre="Bueno",
        color="#4CAF50",
        descripcion=None,
        creado_por=_AUDIT,
        actualizado_por=None,
    )

    assert condicion.nombre == "Bueno"
    assert condicion.color == "#4CAF50"


def test_sede_se_crea_con_los_campos_esperados():
    sede = Sede(id="1", nombre="Prado", descripcion=None, creado_por=_AUDIT, actualizado_por=None)

    assert sede.nombre == "Prado"


def test_lugar_se_crea_con_los_campos_esperados():
    lugar = Lugar(
        id="1",
        nombre="Bodega",
        tipo=TipoLugar.BODEGA,
        sede_id="1",
        creado_por=_AUDIT,
        actualizado_por=None,
    )

    assert lugar.nombre == "Bodega"
    assert lugar.tipo == TipoLugar.BODEGA
    assert lugar.sede_id == "1"


def test_tipo_lugar_tiene_los_cinco_valores_esperados():
    valores = {tipo.value for tipo in TipoLugar}

    assert valores == {"bodega", "bano", "espacio_comun", "oficina", "exterior"}
