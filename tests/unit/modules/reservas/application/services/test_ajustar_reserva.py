from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.reservas.application.dto.ajuste_item import AjusteItemInput
from modules.reservas.application.dto.ajustar_reserva import AjustarReservaInput
from modules.reservas.application.dto.stock_disponible_resultado import (
    StockDisponibleResultado,
)
from modules.reservas.application.services.ajustar_reserva import AjustarReservaService
from modules.reservas.domain.entities.reserva import ItemReserva, Reserva
from modules.reservas.domain.errors import StockDisponibleInsuficienteError
from shared.domain.entities.audit_persona import AuditPersona


def _audit_persona():
    return AuditPersona(id_persona="user-id", nombre="operativo", fecha=datetime.now(UTC))


def _reserva_existente():
    return Reserva.crear(
        "session-1",
        [ItemReserva(producto_codigo="100", ubicacion="A10-1", cantidad=5)],
        None,
        _audit_persona(),
    )


def _resultado_disponible(disponible: int):
    return StockDisponibleResultado(
        producto_codigo="100",
        ubicacion="A10-1",
        stock_fisico=100,
        reservado_otros=0,
        reservado_actual=5,
        disponible=disponible,
    )


@pytest.fixture
def reserva_repository_mock():
    mock = AsyncMock()
    mock.obtener_por_session_id.return_value = None
    mock.crear.side_effect = lambda reserva: reserva.model_copy(update={"id": "id-1"})
    mock.actualizar.side_effect = lambda reserva: reserva
    return mock


@pytest.fixture
def calcular_stock_service_mock():
    mock = AsyncMock()
    mock.ejecutar.return_value = _resultado_disponible(50)
    return mock


@pytest.fixture
def service(reserva_repository_mock, calcular_stock_service_mock):
    return AjustarReservaService(reserva_repository_mock, calcular_stock_service_mock)


async def test_crea_reserva_nueva_con_ajustes_positivos(service, reserva_repository_mock):
    entrada = AjustarReservaInput(
        ajustes=[AjusteItemInput(producto_codigo="100", ubicacion="A10-1", diferencia=5)]
    )

    reserva = await service.ejecutar("session-1", entrada, _audit_persona())

    assert reserva.items == [ItemReserva(producto_codigo="100", ubicacion="A10-1", cantidad=5)]
    reserva_repository_mock.crear.assert_called_once()


async def test_reserva_nueva_ignora_ajustes_negativos_y_no_crea_nada(
    service, reserva_repository_mock
):
    entrada = AjustarReservaInput(
        ajustes=[AjusteItemInput(producto_codigo="100", ubicacion="A10-1", diferencia=-5)]
    )

    reserva = await service.ejecutar("session-1", entrada, _audit_persona())

    assert reserva is None
    reserva_repository_mock.crear.assert_not_called()


async def test_ajusta_reserva_existente_sumando(
    service, reserva_repository_mock, calcular_stock_service_mock
):
    reserva_repository_mock.obtener_por_session_id.return_value = _reserva_existente()
    entrada = AjustarReservaInput(
        ajustes=[AjusteItemInput(producto_codigo="100", ubicacion="A10-1", diferencia=3)]
    )

    reserva = await service.ejecutar("session-1", entrada, _audit_persona())

    assert reserva.items[0].cantidad == 8
    reserva_repository_mock.actualizar.assert_called_once()


async def test_ajuste_que_vacia_la_reserva_la_elimina(
    service, reserva_repository_mock, calcular_stock_service_mock
):
    reserva_repository_mock.obtener_por_session_id.return_value = _reserva_existente()
    entrada = AjustarReservaInput(
        ajustes=[AjusteItemInput(producto_codigo="100", ubicacion="A10-1", diferencia=-5)]
    )

    resultado = await service.ejecutar("session-1", entrada, _audit_persona())

    assert resultado is None
    reserva_repository_mock.eliminar.assert_called_once_with("session-1")
    reserva_repository_mock.actualizar.assert_not_called()


async def test_stock_insuficiente_lanza_error(service, calcular_stock_service_mock):
    calcular_stock_service_mock.ejecutar.return_value = _resultado_disponible(2)
    entrada = AjustarReservaInput(
        ajustes=[AjusteItemInput(producto_codigo="100", ubicacion="A10-1", diferencia=5)]
    )

    with pytest.raises(StockDisponibleInsuficienteError):
        await service.ejecutar("session-1", entrada, _audit_persona())


async def test_actualiza_datos_adicionales_si_se_proveen(
    service, reserva_repository_mock, calcular_stock_service_mock
):
    reserva_repository_mock.obtener_por_session_id.return_value = _reserva_existente()
    entrada = AjustarReservaInput(
        ajustes=[AjusteItemInput(producto_codigo="100", ubicacion="A10-1", diferencia=1)],
        datos_adicionales={"cliente": "Juan"},
    )

    reserva = await service.ejecutar("session-1", entrada, _audit_persona())

    assert reserva.datos_adicionales == {"cliente": "Juan"}


async def test_no_ajustes_negativos_no_valida_stock(service, calcular_stock_service_mock):
    entrada = AjustarReservaInput(
        ajustes=[AjusteItemInput(producto_codigo="100", ubicacion="A10-1", diferencia=-5)]
    )

    await service.ejecutar("session-1", entrada, _audit_persona())

    calcular_stock_service_mock.ejecutar.assert_not_called()
