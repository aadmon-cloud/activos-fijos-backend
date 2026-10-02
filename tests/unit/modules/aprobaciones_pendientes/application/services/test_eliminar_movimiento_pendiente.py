from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.aprobaciones_pendientes.application.services.eliminar_movimiento_pendiente import (
    EliminarMovimientoPendienteService,
)
from modules.aprobaciones_pendientes.domain.entities.movimiento_pendiente import (
    MovimientoPendiente,
)
from modules.aprobaciones_pendientes.domain.errors import (
    MovimientoPendienteNoEncontradoError,
    MovimientoPendienteYaConfirmadoError,
    PendienteNoPerteneceAlUsuarioError,
)
from shared.domain.entities.audit_persona import AuditPersona


def _audit_persona(id_persona="usuario-1"):
    return AuditPersona(id_persona=id_persona, nombre="Ana", fecha=datetime.now(UTC))


def _pendiente(id_persona="usuario-1", estado="pendiente"):
    pendiente = MovimientoPendiente.proponer(
        tipo_propuesto="entrada",
        payload={"producto_codigo": "PROD-001", "cantidad": 10},
        creado_por=_audit_persona(id_persona),
    ).model_copy(update={"id": "pend-1"})
    if estado == "confirmada":
        pendiente = pendiente.confirmar(movimiento_id="mov-1", confirmado_por=_audit_persona())
    return pendiente


@pytest.fixture
def movimiento_pendiente_repository_mock():
    mock = AsyncMock()
    mock.obtener_por_id.return_value = _pendiente()
    return mock


@pytest.fixture
def service(movimiento_pendiente_repository_mock):
    return EliminarMovimientoPendienteService(movimiento_pendiente_repository_mock)


async def test_no_encontrada_lanza_error(service, movimiento_pendiente_repository_mock):
    movimiento_pendiente_repository_mock.obtener_por_id.return_value = None

    with pytest.raises(MovimientoPendienteNoEncontradoError):
        await service.ejecutar("pend-1", usuario_actual_id="usuario-1", es_super_admin=False)


async def test_dueno_puede_eliminar_la_propia(service, movimiento_pendiente_repository_mock):
    await service.ejecutar("pend-1", usuario_actual_id="usuario-1", es_super_admin=False)

    movimiento_pendiente_repository_mock.eliminar.assert_called_once_with("pend-1")


async def test_super_admin_puede_eliminar_la_de_otro(
    service, movimiento_pendiente_repository_mock
):
    await service.ejecutar("pend-1", usuario_actual_id="otro-admin", es_super_admin=True)

    movimiento_pendiente_repository_mock.eliminar.assert_called_once_with("pend-1")


async def test_no_dueno_ni_super_admin_lanza_error(service, movimiento_pendiente_repository_mock):
    with pytest.raises(PendienteNoPerteneceAlUsuarioError):
        await service.ejecutar("pend-1", usuario_actual_id="usuario-2", es_super_admin=False)

    movimiento_pendiente_repository_mock.eliminar.assert_not_called()


async def test_ya_confirmada_lanza_error(service, movimiento_pendiente_repository_mock):
    movimiento_pendiente_repository_mock.obtener_por_id.return_value = _pendiente(
        estado="confirmada"
    )

    with pytest.raises(MovimientoPendienteYaConfirmadoError):
        await service.ejecutar("pend-1", usuario_actual_id="usuario-1", es_super_admin=False)

    movimiento_pendiente_repository_mock.eliminar.assert_not_called()
