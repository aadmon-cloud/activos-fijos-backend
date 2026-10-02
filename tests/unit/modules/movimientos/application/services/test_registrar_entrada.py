from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.movimientos.application.dto.registrar_entrada import RegistrarEntradaInput
from modules.movimientos.application.services.ajustador_de_stock import AjustadorDeStockService
from modules.movimientos.application.services.registrar_entrada import RegistrarEntradaService
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
    mock.obtener.return_value = None
    mock.crear.side_effect = lambda ubicacion, uow=None: ubicacion.model_copy(
        update={"id": "ubic-id"}
    )
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
def ajustador_de_stock(producto_repository_mock, ubicacion_repository_mock):
    return AjustadorDeStockService(producto_repository_mock, ubicacion_repository_mock)


@pytest.fixture
def service(movimiento_repository_mock, ajustador_de_stock):
    return RegistrarEntradaService(
        movimiento_repository_mock,
        ajustador_de_stock,
        fake_unit_of_work_factory,
    )


async def test_producto_no_encontrado_lanza_error(service, producto_repository_mock):
    producto_repository_mock.obtener_por_codigo.return_value = None
    entrada = RegistrarEntradaInput(producto_codigo="NO-EXISTE", cantidad=10)

    with pytest.raises(ProductoNoEncontradoError):
        await service.ejecutar(entrada, _audit_persona())


async def test_crea_ubicacion_si_no_existia(service, ubicacion_repository_mock):
    entrada = RegistrarEntradaInput(producto_codigo="PROD-001", cantidad=10, ubicacion="A10-1")

    await service.ejecutar(entrada, _audit_persona())

    nueva = ubicacion_repository_mock.crear.call_args.args[0]
    assert nueva.ubicacion == "A10-1"
    assert nueva.stock_fisico == 10


async def test_suma_stock_si_ubicacion_ya_existia(service, ubicacion_repository_mock):
    ubicacion_repository_mock.obtener.return_value = Ubicacion.crear(
        "PROD-001", "A10-1", 50, _audit_persona()
    )
    entrada = RegistrarEntradaInput(producto_codigo="PROD-001", cantidad=10, ubicacion="A10-1")

    await service.ejecutar(entrada, _audit_persona())

    actualizada = ubicacion_repository_mock.actualizar.call_args.args[0]
    assert actualizada.stock_fisico == 60


async def test_sin_ubicacion_usa_almacen_general(service, ubicacion_repository_mock):
    entrada = RegistrarEntradaInput(producto_codigo="PROD-001", cantidad=10)

    movimiento = await service.ejecutar(entrada, _audit_persona())

    assert movimiento.ubicacion == "ALMACEN_GENERAL"
    ubicacion_repository_mock.obtener.assert_called_once_with("PROD-001", "ALMACEN_GENERAL")


async def test_recalcula_stock_actual_como_suma_de_ubicaciones(
    service, ubicacion_repository_mock, producto_repository_mock
):
    ubicacion_repository_mock.listar_por_producto.return_value = [
        Ubicacion.crear("PROD-001", "A10-1", 60, _audit_persona()),
        Ubicacion.crear("PROD-001", "A10-2", 30, _audit_persona()),
    ]
    entrada = RegistrarEntradaInput(producto_codigo="PROD-001", cantidad=10, ubicacion="A10-1")

    await service.ejecutar(entrada, _audit_persona())

    producto_actualizado = producto_repository_mock.actualizar.call_args.args[0]
    assert producto_actualizado.stock_actual == 90


async def test_movimiento_creado_tiene_los_datos_correctos(service, movimiento_repository_mock):
    entrada = RegistrarEntradaInput(
        producto_codigo="PROD-001",
        cantidad=10,
        motivo="Compra",
        tipo_origen="compra",
        origen_nombre="Proveedor X",
        ubicacion="A10-1",
    )

    movimiento = await service.ejecutar(entrada, _audit_persona())

    assert movimiento.id == "mov-id"
    assert movimiento.tipo == "entrada"
    assert movimiento.producto_nombre == "Arroz"
    assert movimiento.origen_nombre == "Proveedor X"


async def test_con_uow_externo_no_abre_transaccion_propia(
    movimiento_repository_mock, ajustador_de_stock, ubicacion_repository_mock
):
    unit_of_work_factory_mock = AsyncMock(side_effect=AssertionError("no debería abrir su propia uow"))
    service = RegistrarEntradaService(
        movimiento_repository_mock,
        ajustador_de_stock,
        unit_of_work_factory_mock,
    )
    entrada = RegistrarEntradaInput(producto_codigo="PROD-001", cantidad=10, ubicacion="A10-1")
    uow_externo = object()

    movimiento = await service.ejecutar(entrada, _audit_persona(), uow=uow_externo)

    unit_of_work_factory_mock.assert_not_called()
    assert movimiento.id == "mov-id"
    assert ubicacion_repository_mock.crear.call_args.kwargs["uow"] is uow_externo
    assert movimiento_repository_mock.crear.call_args.kwargs["uow"] is uow_externo
