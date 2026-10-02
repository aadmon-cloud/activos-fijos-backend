from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.inventario_reportes.application.services.obtener_estadisticas_dashboard import (
    ObtenerEstadisticasDashboardService,
)
from modules.movimientos.application.dto.listar_movimientos import ListarMovimientosInput
from modules.movimientos.domain.entities.movimiento import Movimiento
from modules.productos.domain.entities.producto import Producto
from shared.domain.entities.audit_persona import AuditPersona


def _audit():
    return AuditPersona(id_persona="user-id", nombre="admin", fecha=datetime.now(UTC))


def _producto(codigo: str):
    return Producto.crear(
        codigo=codigo,
        nombre=f"Producto {codigo}",
        descripcion=None,
        categoria=None,
        stock_minimo=10,
        precio_unitario=5.0,
        creado_por=_audit(),
    )


def _movimiento():
    return Movimiento(
        id="mov-1",
        tipo="entrada",
        modalidad="individual",
        producto_codigo="PROD-001",
        producto_nombre="Producto 1",
        cantidad=1,
        creado_por=_audit(),
    )


@pytest.fixture
def producto_repository_mock():
    mock = AsyncMock()
    mock.listar_paginado.return_value = ([], 42)
    mock.listar_bajo_stock.return_value = [_producto("PROD-001"), _producto("PROD-002")]
    return mock


@pytest.fixture
def movimiento_repository_mock():
    mock = AsyncMock()
    mock.listar.return_value = ([_movimiento()], 7)
    return mock


@pytest.fixture
def service(producto_repository_mock, movimiento_repository_mock):
    return ObtenerEstadisticasDashboardService(producto_repository_mock, movimiento_repository_mock)


async def test_compone_total_productos_y_bajo_stock_como_conteos(
    service, producto_repository_mock
):
    resultado = await service.ejecutar()

    assert resultado.total_productos == 42
    assert resultado.productos_bajo_stock_conteo == 2
    producto_repository_mock.listar_paginado.assert_called_once_with(pagina=1, limite=1)


async def test_incluye_ultimos_diez_movimientos(service, movimiento_repository_mock):
    resultado = await service.ejecutar()

    assert len(resultado.ultimos_movimientos) == 1
    filtro_llamado = movimiento_repository_mock.listar.call_args_list[0].args[0]
    assert isinstance(filtro_llamado, ListarMovimientosInput)
    assert filtro_llamado.pagina == 1
    assert filtro_llamado.limite == 10


async def test_movimientos_hoy_usa_total_elementos_no_la_lista(
    service, movimiento_repository_mock
):
    resultado = await service.ejecutar()

    assert resultado.movimientos_hoy == 7
    filtro_hoy = movimiento_repository_mock.listar.call_args_list[1].args[0]
    assert filtro_hoy.fecha_desde is not None
    assert filtro_hoy.fecha_desde.hour == 0
