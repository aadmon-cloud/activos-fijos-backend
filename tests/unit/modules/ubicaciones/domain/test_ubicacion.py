from datetime import UTC, datetime

from modules.ubicaciones.domain.entities.ubicacion import Ubicacion
from shared.domain.entities.audit_persona import AuditPersona


def _audit_persona():
    return AuditPersona(id_persona="admin-id", nombre="admin", fecha=datetime.now(UTC))


def test_crear_ubicacion_con_datos_validos():
    ubicacion = Ubicacion.crear(
        producto_codigo="PROD-001",
        ubicacion="  A10-1  ",
        stock_fisico=50,
        creado_por=_audit_persona(),
    )

    assert ubicacion.producto_codigo == "PROD-001"
    assert ubicacion.ubicacion == "A10-1"
    assert ubicacion.stock_fisico == 50
    assert ubicacion.stock_reservado == 0
    assert ubicacion.id is None


def test_actualizar_stock_fisico_cambia_solo_ese_campo():
    ubicacion = Ubicacion.crear(
        producto_codigo="PROD-001",
        ubicacion="A10-1",
        stock_fisico=50,
        creado_por=_audit_persona(),
    )

    actualizador = AuditPersona(id_persona="otro-id", nombre="otro", fecha=datetime.now(UTC))
    actualizada = ubicacion.actualizar_stock_fisico(80, actualizador)

    assert actualizada.stock_fisico == 80
    assert actualizada.producto_codigo == "PROD-001"
    assert actualizada.ubicacion == "A10-1"
    assert actualizada.actualizado_por == actualizador


def test_actualizar_stock_fisico_no_muta_la_original():
    ubicacion = Ubicacion.crear(
        producto_codigo="PROD-001",
        ubicacion="A10-1",
        stock_fisico=50,
        creado_por=_audit_persona(),
    )

    ubicacion.actualizar_stock_fisico(80, _audit_persona())

    assert ubicacion.stock_fisico == 50


def test_stock_disponible_resta_reservado():
    ubicacion = Ubicacion.crear(
        producto_codigo="PROD-001",
        ubicacion="A10-1",
        stock_fisico=50,
        creado_por=_audit_persona(),
    ).model_copy(update={"stock_reservado": 20})

    assert ubicacion.stock_disponible == 30


def test_stock_disponible_nunca_es_negativo():
    ubicacion = Ubicacion.crear(
        producto_codigo="PROD-001",
        ubicacion="A10-1",
        stock_fisico=10,
        creado_por=_audit_persona(),
    ).model_copy(update={"stock_reservado": 999})

    assert ubicacion.stock_disponible == 0
