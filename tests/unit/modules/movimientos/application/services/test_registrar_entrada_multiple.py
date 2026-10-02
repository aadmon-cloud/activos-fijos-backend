from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.movimientos.application.dto.registrar_entrada_multiple import (
    ItemEntradaMultipleInput,
    RegistrarEntradaMultipleInput,
)
from modules.movimientos.application.services.ajustador_de_stock import AjustadorDeStockService
from modules.movimientos.application.services.registrar_entrada_multiple import (
    RegistrarEntradaMultipleService,
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


def _producto(codigo="PROD-001", nombre="Arroz"):
    return Producto.crear(
        codigo=codigo,
        nombre=nombre,
        descripcion=None,
        categoria=None,
        stock_minimo=0,
        precio_unitario=0.0,
        creado_por=_audit_persona(),
    ).model_copy(update={"id": f"id-{codigo}"})


@pytest.fixture
def movimiento_repository_mock():
    mock = AsyncMock()
    mock.crear.side_effect = lambda movimiento, uow=None: movimiento.model_copy(
        update={"id": "mov-multi-1"}
    )
    return mock


@pytest.fixture
def producto_repository_mock():
    mock = AsyncMock()
    mock.obtener_por_codigo.side_effect = lambda codigo: _producto(codigo, f"Producto {codigo}")
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
def ajustador_de_stock(producto_repository_mock, ubicacion_repository_mock):
    return AjustadorDeStockService(producto_repository_mock, ubicacion_repository_mock)


@pytest.fixture
def service(movimiento_repository_mock, ajustador_de_stock):
    return RegistrarEntradaMultipleService(
        movimiento_repository_mock,
        ajustador_de_stock,
        fake_unit_of_work_factory,
    )


def _entrada(productos, ubicacion=None):
    return RegistrarEntradaMultipleInput(
        productos=productos,
        tipo_origen="compra",
        origen_nombre="Proveedor X",
        ubicacion=ubicacion,
        notas=None,
    )


async def test_crea_un_solo_movimiento_con_todos_los_items(
    service, movimiento_repository_mock
):
    entrada = _entrada(
        [
            ItemEntradaMultipleInput(producto_codigo="PROD-001", cantidad=3, ubicacion="A10-1"),
            ItemEntradaMultipleInput(producto_codigo="PROD-002", cantidad=2, ubicacion="A10-2"),
        ]
    )

    movimiento = await service.ejecutar(entrada, _audit_persona())

    assert movimiento_repository_mock.crear.call_count == 1
    assert movimiento.tipo == "entrada"
    assert movimiento.modalidad == "entrada_multiple"
    assert movimiento.cantidad == 5
    assert movimiento.motivo == "Compra"
    assert len(movimiento.productos) == 2


async def test_usa_ubicacion_del_item_si_viene(service, ubicacion_repository_mock):
    entrada = _entrada(
        [ItemEntradaMultipleInput(producto_codigo="PROD-001", cantidad=3, ubicacion="A10-1")]
    )

    movimiento = await service.ejecutar(entrada, _audit_persona())

    assert movimiento.productos[0].ubicacion == "A10-1"
    nueva = ubicacion_repository_mock.crear.call_args.args[0]
    assert nueva.ubicacion == "A10-1"


async def test_usa_ubicacion_global_si_item_no_trae_la_suya(service):
    entrada = _entrada(
        [ItemEntradaMultipleInput(producto_codigo="PROD-001", cantidad=3)],
        ubicacion="BODEGA-GLOBAL",
    )

    movimiento = await service.ejecutar(entrada, _audit_persona())

    assert movimiento.productos[0].ubicacion == "BODEGA-GLOBAL"


async def test_usa_almacen_general_si_no_hay_ninguna_ubicacion(service):
    entrada = _entrada([ItemEntradaMultipleInput(producto_codigo="PROD-001", cantidad=3)])

    movimiento = await service.ejecutar(entrada, _audit_persona())

    assert movimiento.productos[0].ubicacion == "ALMACEN_GENERAL"


async def test_suma_stock_si_la_ubicacion_ya_existia(service, ubicacion_repository_mock):
    ubicacion_repository_mock.obtener.return_value = Ubicacion.crear(
        "PROD-001", "A10-1", 50, _audit_persona()
    )
    entrada = _entrada(
        [ItemEntradaMultipleInput(producto_codigo="PROD-001", cantidad=10, ubicacion="A10-1")]
    )

    await service.ejecutar(entrada, _audit_persona())

    actualizada = ubicacion_repository_mock.actualizar.call_args.args[0]
    assert actualizada.stock_fisico == 60


async def test_recalcula_stock_actual_como_suma_de_ubicaciones(
    service, ubicacion_repository_mock, producto_repository_mock
):
    ubicacion_repository_mock.listar_por_producto.return_value = [
        Ubicacion.crear("PROD-001", "A10-1", 30, _audit_persona()),
        Ubicacion.crear("PROD-001", "A10-2", 15, _audit_persona()),
    ]
    entrada = _entrada(
        [ItemEntradaMultipleInput(producto_codigo="PROD-001", cantidad=10, ubicacion="A10-1")]
    )

    await service.ejecutar(entrada, _audit_persona())

    producto_actualizado = producto_repository_mock.actualizar.call_args.args[0]
    assert producto_actualizado.stock_actual == 45


async def test_producto_no_encontrado_lanza_error(service, producto_repository_mock):
    producto_repository_mock.obtener_por_codigo.side_effect = None
    producto_repository_mock.obtener_por_codigo.return_value = None
    entrada = _entrada([ItemEntradaMultipleInput(producto_codigo="NO-EXISTE", cantidad=3)])

    with pytest.raises(ProductoNoEncontradoError):
        await service.ejecutar(entrada, _audit_persona())


async def test_con_uow_externo_no_abre_transaccion_propia(
    movimiento_repository_mock, ajustador_de_stock, ubicacion_repository_mock
):
    unit_of_work_factory_mock = AsyncMock(side_effect=AssertionError("no debería abrir su propia uow"))
    service = RegistrarEntradaMultipleService(
        movimiento_repository_mock,
        ajustador_de_stock,
        unit_of_work_factory_mock,
    )
    entrada = _entrada(
        [ItemEntradaMultipleInput(producto_codigo="PROD-001", cantidad=3, ubicacion="A10-1")]
    )
    uow_externo = object()

    movimiento = await service.ejecutar(entrada, _audit_persona(), uow=uow_externo)

    unit_of_work_factory_mock.assert_not_called()
    assert movimiento.id == "mov-multi-1"
    assert movimiento_repository_mock.crear.call_args.kwargs["uow"] is uow_externo
