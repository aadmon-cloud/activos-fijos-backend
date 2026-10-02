from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.inventario_reportes.application.services.obtener_reporte_inventario import (
    ObtenerReporteInventarioService,
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
    mock.listar_paginado.return_value = ([], 15)
    mock.listar_bajo_stock.return_value = [_producto("PROD-001")]
    mock.calcular_valor_total.return_value = 4321.0
    return mock


@pytest.fixture
def movimiento_repository_mock():
    mock = AsyncMock()
    mock.listar.return_value = ([_movimiento()], 1)
    return mock


@pytest.fixture
def service(producto_repository_mock, movimiento_repository_mock):
    return ObtenerReporteInventarioService(producto_repository_mock, movimiento_repository_mock)


async def test_compone_los_cuatro_casos_de_uso_atomicos(
    service, producto_repository_mock, movimiento_repository_mock
):
    resultado = await service.ejecutar()

    assert resultado.total_productos == 15
    assert len(resultado.productos_bajo_stock) == 1
    assert resultado.valor_total_inventario == 4321.0
    assert len(resultado.ultimos_movimientos) == 1
    filtro_llamado = movimiento_repository_mock.listar.call_args.args[0]
    assert isinstance(filtro_llamado, ListarMovimientosInput)
    assert filtro_llamado.limite == 10
