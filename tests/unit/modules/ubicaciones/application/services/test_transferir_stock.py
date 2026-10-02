from datetime import UTC, datetime
from unittest.mock import ANY, AsyncMock

import pytest

from modules.ubicaciones.application.dto.transferir_stock import TransferirStockInput
from modules.ubicaciones.application.services.transferir_stock import TransferirStockService
from modules.ubicaciones.domain.entities.ubicacion import Ubicacion
from modules.ubicaciones.domain.errors import StockInsuficienteError, UbicacionNoEncontradaError
from shared.domain.entities.audit_persona import AuditPersona
from tests.unit.modules.ubicaciones.application.services._fakes import (
    fake_unit_of_work_factory,
)


def _audit_persona():
    return AuditPersona(id_persona="admin-id", nombre="admin", fecha=datetime.now(UTC))


def _ubicacion(nombre: str, stock_fisico: int):
    return Ubicacion.crear("PROD-001", nombre, stock_fisico, _audit_persona()).model_copy(
        update={"id": f"id-{nombre}"}
    )


@pytest.fixture
def ubicacion_repository_mock():
    mock = AsyncMock()

    async def obtener(producto_codigo, ubicacion):
        if ubicacion == "A10-1":
            return _ubicacion("A10-1", 50)
        return None

    mock.obtener.side_effect = obtener
    mock.actualizar.side_effect = lambda ubicacion, uow=None: ubicacion
    mock.crear.side_effect = lambda ubicacion, uow=None: ubicacion
    return mock


@pytest.fixture
def registrador_de_movimientos_mock():
    return AsyncMock()


@pytest.fixture
def service(ubicacion_repository_mock, registrador_de_movimientos_mock):
    return TransferirStockService(
        ubicacion_repository_mock, registrador_de_movimientos_mock, fake_unit_of_work_factory
    )


async def test_transfiere_stock_a_ubicacion_existente(service, ubicacion_repository_mock):
    async def obtener(producto_codigo, ubicacion):
        if ubicacion == "A10-1":
            return _ubicacion("A10-1", 50)
        if ubicacion == "A10-2":
            return _ubicacion("A10-2", 10)
        return None

    ubicacion_repository_mock.obtener.side_effect = obtener
    entrada = TransferirStockInput(origen="A10-1", destino="A10-2", cantidad=20)

    await service.ejecutar("PROD-001", entrada, _audit_persona())

    llamadas = ubicacion_repository_mock.actualizar.call_args_list
    origen_actualizado = next(c.args[0] for c in llamadas if c.args[0].ubicacion == "A10-1")
    destino_actualizado = next(c.args[0] for c in llamadas if c.args[0].ubicacion == "A10-2")
    assert origen_actualizado.stock_fisico == 30
    assert destino_actualizado.stock_fisico == 30


async def test_transfiere_stock_crea_destino_si_no_existe(service, ubicacion_repository_mock):
    entrada = TransferirStockInput(origen="A10-1", destino="A10-3", cantidad=20)

    await service.ejecutar("PROD-001", entrada, _audit_persona())

    nueva_ubicacion = ubicacion_repository_mock.crear.call_args.args[0]
    assert nueva_ubicacion.ubicacion == "A10-3"
    assert nueva_ubicacion.stock_fisico == 20


async def test_origen_no_encontrado_lanza_error(service):
    entrada = TransferirStockInput(origen="NO-EXISTE", destino="A10-2", cantidad=10)

    with pytest.raises(UbicacionNoEncontradaError):
        await service.ejecutar("PROD-001", entrada, _audit_persona())


async def test_stock_insuficiente_lanza_error(service):
    entrada = TransferirStockInput(origen="A10-1", destino="A10-2", cantidad=999)

    with pytest.raises(StockInsuficienteError):
        await service.ejecutar("PROD-001", entrada, _audit_persona())


async def test_registra_bitacora_de_movimientos(service, registrador_de_movimientos_mock):
    entrada = TransferirStockInput(origen="A10-1", destino="A10-2", cantidad=20)
    actualizado_por = _audit_persona()

    await service.ejecutar("PROD-001", entrada, actualizado_por)

    registrador_de_movimientos_mock.registrar_transferencia_stock.assert_called_once_with(
        producto_codigo="PROD-001",
        ubicacion_origen="A10-1",
        ubicacion_destino="A10-2",
        cantidad=20,
        creado_por=actualizado_por,
        uow=ANY,
    )
