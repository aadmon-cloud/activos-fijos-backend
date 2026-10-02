from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.productos.application.services.obtener_producto import ObtenerProductoService
from modules.productos.domain.entities.producto import Producto
from modules.productos.domain.errors import ProductoNoEncontradoError
from shared.domain.entities.audit_persona import AuditPersona


def _producto():
    return Producto.crear(
        codigo="PROD-001",
        nombre="Laptop",
        descripcion=None,
        categoria=None,
        stock_minimo=0,
        precio_unitario=0.0,
        creado_por=AuditPersona(id_persona="user-id", nombre="admin", fecha=datetime.now(UTC)),
    )


@pytest.fixture
def producto_repository_mock():
    mock = AsyncMock()
    mock.obtener_por_codigo.return_value = _producto()
    return mock


@pytest.fixture
def service(producto_repository_mock):
    return ObtenerProductoService(producto_repository_mock)


async def test_obtiene_producto_existente(service):
    producto = await service.ejecutar("PROD-001")
    assert producto.codigo == "PROD-001"


async def test_producto_no_encontrado_lanza_error(service, producto_repository_mock):
    producto_repository_mock.obtener_por_codigo.return_value = None

    with pytest.raises(ProductoNoEncontradoError):
        await service.ejecutar("PROD-999")
