from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.aprobaciones_pendientes.application.services.eliminar_movimientos_pendientes_multiples import (
    EliminarMovimientosPendientesMultiplesService,
)
from modules.aprobaciones_pendientes.domain.entities.movimiento_pendiente import (
    MovimientoPendiente,
)
from shared.domain.entities.audit_persona import AuditPersona


def _audit_persona():
    return AuditPersona(id_persona="usuario-1", nombre="Ana", fecha=datetime.now(UTC))


def _pendiente(id_, estado="pendiente"):
    pendiente = MovimientoPendiente.proponer(
        tipo_propuesto="entrada",
        payload={"producto_codigo": "PROD-001", "cantidad": 10},
        creado_por=_audit_persona(),
    ).model_copy(update={"id": id_})
    if estado == "confirmada":
        pendiente = pendiente.confirmar(movimiento_id="mov-1", confirmado_por=_audit_persona())
    return pendiente


@pytest.fixture
def movimiento_pendiente_repository_mock():
    return AsyncMock()


@pytest.fixture
def service(movimiento_pendiente_repository_mock):
    return EliminarMovimientosPendientesMultiplesService(movimiento_pendiente_repository_mock)


async def test_elimina_solo_las_pendientes_existentes(
    service, movimiento_pendiente_repository_mock
):
    movimiento_pendiente_repository_mock.obtener_por_id.side_effect = lambda id_: {
        "pend-1": _pendiente("pend-1"),
        "pend-2": None,
        "pend-3": _pendiente("pend-3", estado="confirmada"),
    }[id_]

    resultado = await service.ejecutar(["pend-1", "pend-2", "pend-3"])

    assert resultado == {"eliminadas": 1, "total_solicitadas": 3}
    movimiento_pendiente_repository_mock.eliminar.assert_called_once_with("pend-1")
