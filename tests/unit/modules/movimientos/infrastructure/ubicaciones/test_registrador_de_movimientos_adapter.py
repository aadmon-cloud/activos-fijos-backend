from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.movimientos.infrastructure.ubicaciones.registrador_de_movimientos_adapter import (
    MovimientosRegistradorDeMovimientosAdapter,
)
from modules.productos.domain.entities.producto import Producto
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
    )


@pytest.fixture
def movimiento_repository_mock():
    return AsyncMock()


@pytest.fixture
def producto_repository_mock():
    mock = AsyncMock()
    mock.obtener_por_codigo.return_value = _producto()
    return mock


@pytest.fixture
def adapter(movimiento_repository_mock, producto_repository_mock):
    return MovimientosRegistradorDeMovimientosAdapter(
        movimiento_repository_mock, producto_repository_mock
    )


async def test_registrar_creacion_ubicacion_crea_un_movimiento(
    adapter, movimiento_repository_mock
):
    creado_por = _audit_persona()
    uow_falso = object()

    await adapter.registrar_creacion_ubicacion(
        producto_codigo="PROD-001",
        ubicacion="A10-1",
        cantidad=50,
        creado_por=creado_por,
        uow=uow_falso,
    )

    movimiento_repository_mock.crear.assert_called_once()
    movimiento = movimiento_repository_mock.crear.call_args.args[0]
    assert movimiento.tipo == "creacion_ubicacion"
    assert movimiento.producto_codigo == "PROD-001"
    assert movimiento.producto_nombre == "Arroz"
    assert movimiento.ubicacion == "A10-1"
    assert movimiento.cantidad == 50
    assert movimiento_repository_mock.crear.call_args.kwargs["uow"] is uow_falso


async def test_registrar_transferencia_stock_crea_un_movimiento(
    adapter, movimiento_repository_mock
):
    creado_por = _audit_persona()

    await adapter.registrar_transferencia_stock(
        producto_codigo="PROD-001",
        ubicacion_origen="A10-1",
        ubicacion_destino="A10-2",
        cantidad=20,
        creado_por=creado_por,
    )

    movimiento = movimiento_repository_mock.crear.call_args.args[0]
    assert movimiento.tipo == "transferencia_ubicacion"
    assert movimiento.ubicacion_origen == "A10-1"
    assert movimiento.ubicacion_destino == "A10-2"
    assert movimiento.cantidad == 20


async def test_usa_el_codigo_como_nombre_si_el_producto_no_existe(
    adapter, movimiento_repository_mock, producto_repository_mock
):
    producto_repository_mock.obtener_por_codigo.return_value = None

    await adapter.registrar_creacion_ubicacion(
        producto_codigo="NO-EXISTE",
        ubicacion="A10-1",
        cantidad=1,
        creado_por=_audit_persona(),
    )

    movimiento = movimiento_repository_mock.crear.call_args.args[0]
    assert movimiento.producto_nombre == "NO-EXISTE"
