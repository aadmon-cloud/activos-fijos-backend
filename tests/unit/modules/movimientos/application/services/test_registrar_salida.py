from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.movimientos.application.dto.registrar_salida import RegistrarSalidaInput
from modules.movimientos.application.services.ajustador_de_stock import AjustadorDeStockService
from modules.movimientos.application.services.registrar_salida import RegistrarSalidaService
from modules.movimientos.domain.errors import (
    MovimientoStockInsuficienteError,
    MovimientoUbicacionNoEncontradaError,
)
from modules.productos.domain.entities.producto import Producto
from modules.productos.domain.errors import ProductoNoEncontradoError
from modules.ubicaciones.domain.entities.ubicacion import Ubicacion
from shared.domain.entities.audit_persona import AuditPersona
from tests.unit.modules.movimientos.application.services._fakes import (
    fake_unit_of_work_factory,
)


def _audit_persona():
    return AuditPersona(id_persona="admin-id", nombre="admin", fecha=datetime.now(UTC))


def _producto():
    return Producto.crear(
        codigo="PROD-001",
        nombre="Arroz",
        descripcion=None,
        categoria=None,
        stock_minimo=0,
        precio_unitario=0.0,
        creado_por=_audit_persona(),
    ).model_copy(update={"id": "id-1"})


@pytest.fixture
def producto_repository_mock():
    mock = AsyncMock()
    mock.obtener_por_codigo.return_value = _producto()
    mock.actualizar.side_effect = lambda producto, uow=None: producto
    return mock


@pytest.fixture
def ubicacion_repository_mock():
    mock = AsyncMock()
    mock.obtener.return_value = Ubicacion.crear("PROD-001", "A10-1", 50, _audit_persona())
    mock.actualizar.side_effect = lambda ubicacion, uow=None: ubicacion
    mock.listar_por_producto.return_value = []
    return mock


@pytest.fixture
def movimiento_repository_mock():
    mock = AsyncMock()
    mock.crear.side_effect = lambda movimiento, uow=None: movimiento.model_copy(
        update={"id": "mov-id"}
    )
    return mock


@pytest.fixture
def generador_secuencial_mock():
    mock = AsyncMock()
    mock.siguiente.return_value = "RM-001"
    return mock


@pytest.fixture
def ajustador_de_stock(producto_repository_mock, ubicacion_repository_mock):
    return AjustadorDeStockService(producto_repository_mock, ubicacion_repository_mock)


@pytest.fixture
def service(movimiento_repository_mock, ajustador_de_stock, generador_secuencial_mock):
    return RegistrarSalidaService(
        movimiento_repository_mock,
        ajustador_de_stock,
        generador_secuencial_mock,
        fake_unit_of_work_factory,
    )


async def test_producto_no_encontrado_lanza_error(service, producto_repository_mock):
    producto_repository_mock.obtener_por_codigo.return_value = None
    entrada = RegistrarSalidaInput(producto_codigo="NO-EXISTE", cantidad=10, ubicacion="A10-1")

    with pytest.raises(ProductoNoEncontradoError):
        await service.ejecutar(entrada, _audit_persona())


async def test_ubicacion_no_encontrada_lanza_error(service, ubicacion_repository_mock):
    ubicacion_repository_mock.obtener.return_value = None
    entrada = RegistrarSalidaInput(producto_codigo="PROD-001", cantidad=10, ubicacion="NO-EXISTE")

    with pytest.raises(MovimientoUbicacionNoEncontradaError):
        await service.ejecutar(entrada, _audit_persona())


async def test_stock_insuficiente_lanza_error(service):
    entrada = RegistrarSalidaInput(producto_codigo="PROD-001", cantidad=999, ubicacion="A10-1")

    with pytest.raises(MovimientoStockInsuficienteError):
        await service.ejecutar(entrada, _audit_persona())


async def test_descuenta_stock_de_la_ubicacion(service, ubicacion_repository_mock):
    entrada = RegistrarSalidaInput(producto_codigo="PROD-001", cantidad=20, ubicacion="A10-1")

    await service.ejecutar(entrada, _audit_persona())

    actualizada = ubicacion_repository_mock.actualizar.call_args.args[0]
    assert actualizada.stock_fisico == 30


async def test_genera_remision(service, generador_secuencial_mock):
    entrada = RegistrarSalidaInput(producto_codigo="PROD-001", cantidad=20, ubicacion="A10-1")

    movimiento = await service.ejecutar(entrada, _audit_persona())

    generador_secuencial_mock.siguiente.assert_called_once()
    assert generador_secuencial_mock.siguiente.call_args.kwargs["nombre"] == "remision"
    assert generador_secuencial_mock.siguiente.call_args.kwargs["prefijo"] == "RM"
    assert movimiento.remision == "RM-001"


async def test_recalcula_stock_actual_como_suma_de_ubicaciones(
    service, ubicacion_repository_mock, producto_repository_mock
):
    ubicacion_repository_mock.listar_por_producto.return_value = [
        Ubicacion.crear("PROD-001", "A10-1", 30, _audit_persona()),
        Ubicacion.crear("PROD-001", "A10-2", 15, _audit_persona()),
    ]
    entrada = RegistrarSalidaInput(producto_codigo="PROD-001", cantidad=20, ubicacion="A10-1")

    await service.ejecutar(entrada, _audit_persona())

    producto_actualizado = producto_repository_mock.actualizar.call_args.args[0]
    assert producto_actualizado.stock_actual == 45


async def test_con_uow_externo_no_abre_transaccion_propia(
    movimiento_repository_mock,
    ajustador_de_stock,
    ubicacion_repository_mock,
    generador_secuencial_mock,
):
    unit_of_work_factory_mock = AsyncMock(side_effect=AssertionError("no debería abrir su propia uow"))
    service = RegistrarSalidaService(
        movimiento_repository_mock,
        ajustador_de_stock,
        generador_secuencial_mock,
        unit_of_work_factory_mock,
    )
    entrada = RegistrarSalidaInput(producto_codigo="PROD-001", cantidad=20, ubicacion="A10-1")
    uow_externo = object()

    movimiento = await service.ejecutar(entrada, _audit_persona(), uow=uow_externo)

    unit_of_work_factory_mock.assert_not_called()
    assert movimiento.remision == "RM-001"
    assert ubicacion_repository_mock.actualizar.call_args.kwargs["uow"] is uow_externo
    assert movimiento_repository_mock.crear.call_args.kwargs["uow"] is uow_externo
