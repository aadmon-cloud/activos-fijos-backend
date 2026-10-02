from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.reservas.application.services.calcular_stock_disponible import (
    CalcularStockDisponibleService,
)
from modules.reservas.domain.entities.reserva import ItemReserva, Reserva
from modules.ubicaciones.domain.entities.ubicacion import Ubicacion
from modules.ubicaciones.domain.errors import UbicacionNoEncontradaError
from shared.domain.entities.audit_persona import AuditPersona


def _audit_persona():
    return AuditPersona(id_persona="user-id", nombre="operativo", fecha=datetime.now(UTC))


def _ubicacion(stock_fisico: int):
    return Ubicacion.crear("100", "A10-1", stock_fisico, _audit_persona())


def _reserva(session_id: str, cantidad: int):
    return Reserva.crear(
        session_id,
        [ItemReserva(producto_codigo="100", ubicacion="A10-1", cantidad=cantidad)],
        None,
        _audit_persona(),
    )


@pytest.fixture
def ubicacion_repository_mock():
    mock = AsyncMock()
    mock.obtener.return_value = _ubicacion(100)
    return mock


@pytest.fixture
def reserva_repository_mock():
    mock = AsyncMock()
    mock.listar_activas_por_producto_ubicacion.return_value = []
    return mock


@pytest.fixture
def service(ubicacion_repository_mock, reserva_repository_mock):
    return CalcularStockDisponibleService(ubicacion_repository_mock, reserva_repository_mock)


async def test_disponible_es_stock_fisico_sin_reservas(service):
    resultado = await service.ejecutar("100", "A10-1")

    assert resultado.stock_fisico == 100
    assert resultado.reservado_otros == 0
    assert resultado.reservado_actual == 0
    assert resultado.disponible == 100


async def test_descuenta_reservas_de_otras_sesiones(service, reserva_repository_mock):
    reserva_repository_mock.listar_activas_por_producto_ubicacion.return_value = [
        _reserva("session-otro", 30)
    ]

    resultado = await service.ejecutar("100", "A10-1", session_id_actual="session-mio")

    assert resultado.reservado_otros == 30
    assert resultado.reservado_actual == 0
    assert resultado.disponible == 70


async def test_descuenta_reserva_de_la_sesion_actual_por_separado(service, reserva_repository_mock):
    reserva_repository_mock.listar_activas_por_producto_ubicacion.return_value = [
        _reserva("session-otro", 30),
        _reserva("session-mio", 20),
    ]

    resultado = await service.ejecutar("100", "A10-1", session_id_actual="session-mio")

    assert resultado.reservado_otros == 30
    assert resultado.reservado_actual == 20
    assert resultado.disponible == 50


async def test_disponible_nunca_es_negativo(service, reserva_repository_mock):
    reserva_repository_mock.listar_activas_por_producto_ubicacion.return_value = [
        _reserva("session-otro", 999)
    ]

    resultado = await service.ejecutar("100", "A10-1")

    assert resultado.disponible == 0


async def test_ubicacion_no_encontrada_lanza_error(service, ubicacion_repository_mock):
    ubicacion_repository_mock.obtener.return_value = None

    with pytest.raises(UbicacionNoEncontradaError):
        await service.ejecutar("100", "NO-EXISTE")
