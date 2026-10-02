from datetime import UTC, datetime

import pytest

from modules.mercados_predefinidos.domain.entities.mercado_predefinido import (
    MercadoPredefinido,
    ProductoKit,
)
from modules.mercados_predefinidos.domain.errors import MercadoProductosVacioError
from shared.domain.entities.audit_persona import AuditPersona


def _audit_persona():
    return AuditPersona(id_persona="admin-id", nombre="admin", fecha=datetime.now(UTC))


def _productos():
    return [
        ProductoKit(producto_id="100", cantidad=2, producto_nombre="ARROZ"),
        ProductoKit(producto_id="200", cantidad=1, producto_nombre="ACEITE"),
    ]


def test_crear_mercado_con_datos_validos():
    mercado = MercadoPredefinido.crear(
        nombre="  KIT_BASICO  ",
        descripcion="  Kit básico  ",
        productos=_productos(),
        creado_por=_audit_persona(),
    )

    assert mercado.nombre == "KIT_BASICO"
    assert mercado.descripcion == "Kit básico"
    assert len(mercado.productos) == 2
    assert mercado.activo is True
    assert mercado.id is None


def test_crear_mercado_sin_productos_lanza_error():
    with pytest.raises(MercadoProductosVacioError):
        MercadoPredefinido.crear(
            nombre="KIT_VACIO",
            descripcion=None,
            productos=[],
            creado_por=_audit_persona(),
        )


def test_actualizar_aplica_solo_los_campos_provistos():
    mercado = MercadoPredefinido.crear(
        nombre="KIT_BASICO",
        descripcion="Original",
        productos=_productos(),
        creado_por=_audit_persona(),
    )

    actualizador = AuditPersona(id_persona="otro-id", nombre="otro", fecha=datetime.now(UTC))
    actualizado = mercado.actualizar(actualizador, activo=False)

    assert actualizado.activo is False
    assert actualizado.descripcion == "Original"
    assert actualizado.productos == mercado.productos
    assert actualizado.nombre == "KIT_BASICO"


def test_actualizar_no_muta_el_original():
    mercado = MercadoPredefinido.crear(
        nombre="KIT_BASICO",
        descripcion=None,
        productos=_productos(),
        creado_por=_audit_persona(),
    )

    mercado.actualizar(_audit_persona(), activo=False)

    assert mercado.activo is True


def test_actualizar_con_productos_vacios_lanza_error():
    mercado = MercadoPredefinido.crear(
        nombre="KIT_BASICO",
        descripcion=None,
        productos=_productos(),
        creado_por=_audit_persona(),
    )

    with pytest.raises(MercadoProductosVacioError):
        mercado.actualizar(_audit_persona(), productos=[])
