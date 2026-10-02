from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.movimientos.application.services.confirmar_reserva import ConfirmarReservaService
from modules.movimientos.domain.entities.movimiento import Movimiento
from modules.movimientos.domain.errors import ModalidadReservaNoSoportadaError
from modules.reservas.domain.entities.reserva import ItemReserva, Reserva
from modules.reservas.domain.errors import ReservaNoEncontradaError
from shared.domain.entities.audit_persona import AuditPersona


def _audit_persona():
    return AuditPersona(id_persona="admin-id", nombre="admin", fecha=datetime.now(UTC))


def _reserva(datos_adicionales=None):
    return Reserva.crear(
        session_id="session-1",
        items=[ItemReserva(producto_codigo="PROD-001", ubicacion="A10-1", cantidad=5)],
        datos_adicionales=datos_adicionales,
        creado_por=_audit_persona(),
    ).model_copy(update={"id": "reserva-1"})


def _movimiento():
    return Movimiento.registrar_salida(
        producto_codigo="PROD-001",
        producto_nombre="Arroz",
        cantidad=5,
        motivo=None,
        cliente_destino=None,
        ubicacion="A10-1",
        notas=None,
        remision="RM-001",
        creado_por=_audit_persona(),
    ).model_copy(update={"id": "mov-1"})


@pytest.fixture
def reserva_repository_mock():
    mock = AsyncMock()
    mock.obtener_por_session_id.return_value = _reserva()
    return mock


@pytest.fixture
def confirmar_normal_service_mock():
    mock = AsyncMock()
    mock.ejecutar.return_value = [_movimiento()]
    return mock


@pytest.fixture
def confirmar_kit_service_mock():
    mock = AsyncMock()
    mock.ejecutar.return_value = _movimiento().model_copy(update={"modalidad": "kit"})
    return mock


@pytest.fixture
def confirmar_multiple_service_mock():
    mock = AsyncMock()
    mock.ejecutar.return_value = _movimiento().model_copy(update={"modalidad": "multiple"})
    return mock


@pytest.fixture
def service(
    reserva_repository_mock,
    confirmar_normal_service_mock,
    confirmar_kit_service_mock,
    confirmar_multiple_service_mock,
):
    return ConfirmarReservaService(
        reserva_repository_mock,
        confirmar_normal_service_mock,
        confirmar_kit_service_mock,
        confirmar_multiple_service_mock,
    )


async def test_reserva_no_encontrada_lanza_error(service, reserva_repository_mock):
    reserva_repository_mock.obtener_por_session_id.return_value = None

    with pytest.raises(ReservaNoEncontradaError):
        await service.ejecutar("session-1", _audit_persona())


async def test_despacha_a_normal_sin_datos_adicionales(
    service, confirmar_normal_service_mock, confirmar_kit_service_mock
):
    resultado = await service.ejecutar("session-1", _audit_persona())

    confirmar_normal_service_mock.ejecutar.assert_called_once()
    confirmar_kit_service_mock.ejecutar.assert_not_called()
    assert len(resultado) == 1


async def test_despacha_a_kit_por_tipo(
    service, reserva_repository_mock, confirmar_kit_service_mock, confirmar_normal_service_mock
):
    reserva_repository_mock.obtener_por_session_id.return_value = _reserva({"tipo": "kit"})

    resultado = await service.ejecutar("session-1", _audit_persona())

    confirmar_kit_service_mock.ejecutar.assert_called_once()
    confirmar_normal_service_mock.ejecutar.assert_not_called()
    assert len(resultado) == 1  # el único movimiento del kit, envuelto en lista


async def test_despacha_a_kit_por_kit_nombre(
    service, reserva_repository_mock, confirmar_kit_service_mock
):
    reserva_repository_mock.obtener_por_session_id.return_value = _reserva(
        {"kitNombre": "Mercado Básico"}
    )

    await service.ejecutar("session-1", _audit_persona())

    confirmar_kit_service_mock.ejecutar.assert_called_once()


async def test_despacha_a_multiple_por_tipo(
    service,
    reserva_repository_mock,
    confirmar_multiple_service_mock,
    confirmar_normal_service_mock,
    confirmar_kit_service_mock,
):
    reserva_repository_mock.obtener_por_session_id.return_value = _reserva({"tipo": "multiple"})

    resultado = await service.ejecutar("session-1", _audit_persona())

    confirmar_multiple_service_mock.ejecutar.assert_called_once()
    confirmar_normal_service_mock.ejecutar.assert_not_called()
    confirmar_kit_service_mock.ejecutar.assert_not_called()
    assert len(resultado) == 1  # el único movimiento múltiple, envuelto en lista


async def test_modalidad_desconocida_lanza_error(service, reserva_repository_mock):
    reserva_repository_mock.obtener_por_session_id.return_value = _reserva(
        {"tipo": "algo-desconocido"}
    )

    with pytest.raises(ModalidadReservaNoSoportadaError):
        await service.ejecutar("session-1", _audit_persona())
