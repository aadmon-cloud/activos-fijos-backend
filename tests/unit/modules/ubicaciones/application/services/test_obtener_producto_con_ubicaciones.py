from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.productos.domain.entities.producto import Producto
from modules.productos.domain.errors import ProductoNoEncontradoError
from modules.ubicaciones.application.services.obtener_producto_con_ubicaciones import (
    ObtenerProductoConUbicacionesService,
)
from modules.ubicaciones.domain.entities.ubicacion import Ubicacion
from shared.domain.entities.audit_persona import AuditPersona


def _audit_persona():
    return AuditPersona(id_persona="admin-id", nombre="admin", fecha=datetime.now(UTC))


def _producto():
    return Producto.crear(
        codigo="PROD-001",
        nombre="Laptop",
        descripcion=None,
        categoria=None,
        stock_minimo=0,
        precio_unitario=0.0,
        creado_por=_audit_persona(),
    )


@pytest.fixture
def producto_repository_mock():
    mock = AsyncMock()
    mock.obtener_por_codigo.return_value = _producto()
    return mock


@pytest.fixture
def ubicacion_repository_mock():
    mock = AsyncMock()
    mock.listar_por_producto.return_value = [
        Ubicacion.crear("PROD-001", "A10-1", 50, _audit_persona()),
    ]
    return mock


@pytest.fixture
def service(ubicacion_repository_mock, producto_repository_mock):
    return ObtenerProductoConUbicacionesService(ubicacion_repository_mock, producto_repository_mock)


async def test_obtiene_producto_con_sus_ubicaciones(service):
    producto, ubicaciones = await service.ejecutar("PROD-001")

    assert producto.codigo == "PROD-001"
    assert len(ubicaciones) == 1
    assert ubicaciones[0].ubicacion == "A10-1"


async def test_producto_no_encontrado_lanza_error(service, producto_repository_mock):
    producto_repository_mock.obtener_por_codigo.return_value = None

    with pytest.raises(ProductoNoEncontradoError):
        await service.ejecutar("NO-EXISTE")
