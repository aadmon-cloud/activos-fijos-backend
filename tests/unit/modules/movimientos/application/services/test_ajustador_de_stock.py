from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.movimientos.application.services.ajustador_de_stock import AjustadorDeStockService
from modules.movimientos.domain.errors import (
    MovimientoStockInsuficienteError,
    MovimientoUbicacionNoEncontradaError,
)
from modules.productos.domain.entities.producto import Producto
from modules.productos.domain.errors import ProductoNoEncontradoError
from modules.ubicaciones.domain.entities.ubicacion import Ubicacion
from shared.domain.entities.audit_persona import AuditPersona


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
    mock.crear.side_effect = lambda ubicacion, uow=None: ubicacion.model_copy(
        update={"id": "ubic-id"}
    )
    mock.actualizar.side_effect = lambda ubicacion, uow=None: ubicacion
    mock.listar_por_producto.return_value = []
    return mock


@pytest.fixture
def ajustador(producto_repository_mock, ubicacion_repository_mock):
    return AjustadorDeStockService(producto_repository_mock, ubicacion_repository_mock)


async def test_descontar_producto_no_encontrado_lanza_error(ajustador, producto_repository_mock):
    producto_repository_mock.obtener_por_codigo.return_value = None

    with pytest.raises(ProductoNoEncontradoError):
        await ajustador.descontar("NO-EXISTE", "A10-1", 10, _audit_persona(), uow=object())


async def test_descontar_ubicacion_no_encontrada_lanza_error(ajustador, ubicacion_repository_mock):
    ubicacion_repository_mock.obtener.return_value = None

    with pytest.raises(MovimientoUbicacionNoEncontradaError):
        await ajustador.descontar("PROD-001", "NO-EXISTE", 10, _audit_persona(), uow=object())


async def test_descontar_stock_insuficiente_lanza_error(ajustador):
    with pytest.raises(MovimientoStockInsuficienteError):
        await ajustador.descontar("PROD-001", "A10-1", 999, _audit_persona(), uow=object())


async def test_descontar_resta_stock_de_la_ubicacion(ajustador, ubicacion_repository_mock):
    await ajustador.descontar("PROD-001", "A10-1", 20, _audit_persona(), uow=object())

    actualizada = ubicacion_repository_mock.actualizar.call_args.args[0]
    assert actualizada.stock_fisico == 30


async def test_descontar_recalcula_stock_actual_como_suma_de_ubicaciones(
    ajustador, ubicacion_repository_mock, producto_repository_mock
):
    ubicacion_repository_mock.listar_por_producto.return_value = [
        Ubicacion.crear("PROD-001", "A10-1", 30, _audit_persona()),
        Ubicacion.crear("PROD-001", "A10-2", 15, _audit_persona()),
    ]

    producto = await ajustador.descontar("PROD-001", "A10-1", 20, _audit_persona(), uow=object())

    assert producto.stock_actual == 45


async def test_incrementar_producto_no_encontrado_lanza_error(ajustador, producto_repository_mock):
    producto_repository_mock.obtener_por_codigo.return_value = None

    with pytest.raises(ProductoNoEncontradoError):
        await ajustador.incrementar("NO-EXISTE", "A10-1", 10, _audit_persona(), uow=object())


async def test_incrementar_crea_ubicacion_si_no_existia(ajustador, ubicacion_repository_mock):
    ubicacion_repository_mock.obtener.return_value = None

    await ajustador.incrementar("PROD-001", "A10-1", 10, _audit_persona(), uow=object())

    nueva = ubicacion_repository_mock.crear.call_args.args[0]
    assert nueva.ubicacion == "A10-1"
    assert nueva.stock_fisico == 10


async def test_incrementar_suma_stock_si_ubicacion_ya_existia(ajustador, ubicacion_repository_mock):
    await ajustador.incrementar("PROD-001", "A10-1", 10, _audit_persona(), uow=object())

    actualizada = ubicacion_repository_mock.actualizar.call_args.args[0]
    assert actualizada.stock_fisico == 60


async def test_incrementar_recalcula_stock_actual_como_suma_de_ubicaciones(
    ajustador, ubicacion_repository_mock
):
    ubicacion_repository_mock.listar_por_producto.return_value = [
        Ubicacion.crear("PROD-001", "A10-1", 60, _audit_persona()),
        Ubicacion.crear("PROD-001", "A10-2", 30, _audit_persona()),
    ]

    producto = await ajustador.incrementar("PROD-001", "A10-1", 10, _audit_persona(), uow=object())

    assert producto.stock_actual == 90
