from unittest.mock import AsyncMock

import pytest

from modules.reservas.application.services.eliminar_reserva import EliminarReservaService
from modules.reservas.domain.errors import ReservaNoEncontradaError


@pytest.fixture
def reserva_repository_mock():
    mock = AsyncMock()
    mock.eliminar.return_value = True
    return mock


@pytest.fixture
def service(reserva_repository_mock):
    return EliminarReservaService(reserva_repository_mock)


async def test_elimina_reserva_existente(service, reserva_repository_mock):
    await service.ejecutar("session-1")
    reserva_repository_mock.eliminar.assert_called_once_with("session-1")


async def test_reserva_no_encontrada_lanza_error(service, reserva_repository_mock):
    reserva_repository_mock.eliminar.return_value = False

    with pytest.raises(ReservaNoEncontradaError):
        await service.ejecutar("no-existe")
