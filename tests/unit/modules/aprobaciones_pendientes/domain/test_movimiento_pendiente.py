from datetime import UTC, datetime

import pytest

from modules.aprobaciones_pendientes.domain.entities.movimiento_pendiente import (
    MovimientoPendiente,
)
from modules.aprobaciones_pendientes.domain.errors import MovimientoPendienteYaConfirmadoError
from shared.domain.entities.audit_persona import AuditPersona


def _audit_persona(id_persona="usuario-1", nombre="Ana"):
    return AuditPersona(id_persona=id_persona, nombre=nombre, fecha=datetime.now(UTC))


def test_proponer_queda_en_estado_pendiente():
    pendiente = MovimientoPendiente.proponer(
        tipo_propuesto="entrada",
        payload={"producto_codigo": "PROD-001", "cantidad": 10},
        creado_por=_audit_persona(),
    )

    assert pendiente.estado == "pendiente"
    assert pendiente.movimiento_id is None
    assert pendiente.confirmado_por is None
    assert pendiente.tipo_propuesto == "entrada"


def test_confirmar_cambia_estado_y_guarda_referencias():
    pendiente = MovimientoPendiente.proponer(
        tipo_propuesto="salida",
        payload={"producto_codigo": "PROD-001", "cantidad": 5, "ubicacion": "A10-1"},
        creado_por=_audit_persona(),
    ).model_copy(update={"id": "pend-1"})
    super_admin = _audit_persona(id_persona="admin-1", nombre="Admin")

    confirmada = pendiente.confirmar(movimiento_id="mov-1", confirmado_por=super_admin)

    assert confirmada.estado == "confirmada"
    assert confirmada.movimiento_id == "mov-1"
    assert confirmada.confirmado_por == super_admin
    assert pendiente.estado == "pendiente"  # el original no se muta


def test_confirmar_una_ya_confirmada_lanza_error():
    pendiente = MovimientoPendiente.proponer(
        tipo_propuesto="entrada",
        payload={"producto_codigo": "PROD-001", "cantidad": 10},
        creado_por=_audit_persona(),
    ).confirmar(movimiento_id="mov-1", confirmado_por=_audit_persona())

    with pytest.raises(MovimientoPendienteYaConfirmadoError):
        pendiente.confirmar(movimiento_id="mov-2", confirmado_por=_audit_persona())


def test_exigir_eliminable_lanza_error_si_ya_esta_confirmada():
    pendiente = MovimientoPendiente.proponer(
        tipo_propuesto="entrada",
        payload={"producto_codigo": "PROD-001", "cantidad": 10},
        creado_por=_audit_persona(),
    ).confirmar(movimiento_id="mov-1", confirmado_por=_audit_persona())

    with pytest.raises(MovimientoPendienteYaConfirmadoError):
        pendiente.exigir_eliminable()


def test_exigir_eliminable_no_lanza_si_esta_pendiente():
    pendiente = MovimientoPendiente.proponer(
        tipo_propuesto="entrada",
        payload={"producto_codigo": "PROD-001", "cantidad": 10},
        creado_por=_audit_persona(),
    )

    pendiente.exigir_eliminable()  # no debe lanzar


def test_pertenece_a_compara_por_id_persona():
    pendiente = MovimientoPendiente.proponer(
        tipo_propuesto="entrada",
        payload={"producto_codigo": "PROD-001", "cantidad": 10},
        creado_por=_audit_persona(id_persona="usuario-1"),
    )

    assert pendiente.pertenece_a("usuario-1") is True
    assert pendiente.pertenece_a("usuario-2") is False
