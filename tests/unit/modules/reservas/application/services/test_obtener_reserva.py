from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.reservas.application.services.obtener_reserva import ObtenerReservaService
from modules.reservas.domain.entities.reserva import ItemReserva, Reserva
from modules.reservas.domain.errors import ReservaNoEncontradaError
from shared.domain.entities.audit_persona import AuditPersona


def _reserva():
    return Reserva.crear(
        "session-1",
        [ItemReserva(producto_codigo="100", ubicacion="A10-1", cantidad=5)],
        None,
        AuditPersona(id_persona="user-id", nombre="operativo", fecha=datetime.now(UTC)),
    )


@pytest.fixture
def reserva_repository_mock():
    mock = AsyncMock()
    mock.obtener_por_session_id.return_value = _reserva()
    return mock


@pytest.fixture
def service(reserva_repository_mock):
    return ObtenerReservaService(reserva_repository_mock)


async def test_obtiene_reserva_existente(service):
    reserva = await service.ejecutar("session-1")
    assert reserva.session_id == "session-1"


async def test_reserva_no_encontrada_lanza_error(service, reserva_repository_mock):
    reserva_repository_mock.obtener_por_session_id.return_value = None

    with pytest.raises(ReservaNoEncontradaError):
        await service.ejecutar("no-existe")
