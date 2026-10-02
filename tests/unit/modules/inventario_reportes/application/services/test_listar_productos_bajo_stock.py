from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.inventario_reportes.application.services.listar_productos_bajo_stock import (
    ListarProductosBajoStockService,
)
from modules.productos.domain.entities.producto import Producto
from shared.domain.entities.audit_persona import AuditPersona


def _producto(codigo: str):
    return Producto.crear(
        codigo=codigo,
        nombre=f"Producto {codigo}",
        descripcion=None,
        categoria=None,
        stock_minimo=10,
        precio_unitario=5.0,
        creado_por=AuditPersona(id_persona="user-id", nombre="admin", fecha=datetime.now(UTC)),
    )


@pytest.fixture
def producto_repository_mock():
    mock = AsyncMock()
    mock.listar_bajo_stock.return_value = [_producto("PROD-001")]
    return mock


async def test_delega_directamente_en_el_repositorio(producto_repository_mock):
    service = ListarProductosBajoStockService(producto_repository_mock)

    resultado = await service.ejecutar()

    assert len(resultado) == 1
    producto_repository_mock.listar_bajo_stock.assert_called_once_with()
