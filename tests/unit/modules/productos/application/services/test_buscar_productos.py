from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.productos.application.services.buscar_productos import BuscarProductosService
from modules.productos.domain.entities.producto import Producto
from shared.domain.entities.audit_persona import AuditPersona


@pytest.fixture
def producto_repository_mock():
    mock = AsyncMock()
    mock.buscar_por_texto.return_value = [
        Producto.crear(
            codigo="PROD-001",
            nombre="Laptop HP",
            descripcion=None,
            categoria=None,
            stock_minimo=0,
            precio_unitario=0.0,
            creado_por=AuditPersona(
                id_persona="user-id", nombre="admin", fecha=datetime.now(UTC)
            ),
        )
    ]
    return mock


@pytest.fixture
def service(producto_repository_mock):
    return BuscarProductosService(producto_repository_mock)


async def test_busca_productos_por_texto(service, producto_repository_mock):
    resultado = await service.ejecutar("laptop")

    assert len(resultado) == 1
    assert resultado[0].codigo == "PROD-001"
    producto_repository_mock.buscar_por_texto.assert_called_once_with("laptop")
