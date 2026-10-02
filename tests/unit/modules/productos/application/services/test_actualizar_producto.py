from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.productos.application.dto.actualizar_producto import ActualizarProductoInput
from modules.productos.application.services.actualizar_producto import (
    ActualizarProductoService,
)
from modules.productos.domain.entities.producto import Producto
from modules.productos.domain.errors import ProductoNoEncontradoError
from shared.domain.entities.audit_persona import AuditPersona


def _actualizado_por():
    return AuditPersona(id_persona="user-id", nombre="admin", fecha=datetime.now(UTC))


def _producto_existente():
    return Producto.crear(
        codigo="PROD-001",
        nombre="Laptop",
        descripcion=None,
        categoria=None,
        stock_minimo=0,
        precio_unitario=0.0,
        creado_por=_actualizado_por(),
    ).model_copy(update={"id": "id-1"})


@pytest.fixture
def producto_repository_mock():
    mock = AsyncMock()
    mock.obtener_por_codigo.return_value = _producto_existente()
    mock.actualizar.side_effect = lambda producto: producto
    return mock


@pytest.fixture
def service(producto_repository_mock):
    return ActualizarProductoService(producto_repository_mock)


async def test_actualiza_producto_existente(service, producto_repository_mock):
    entrada = ActualizarProductoInput(nombre="Laptop HP")

    producto = await service.ejecutar("PROD-001", entrada, _actualizado_por())

    assert producto.nombre == "Laptop HP"
    producto_repository_mock.obtener_por_codigo.assert_called_once_with("PROD-001")


async def test_producto_no_encontrado_lanza_error(service, producto_repository_mock):
    producto_repository_mock.obtener_por_codigo.return_value = None
    entrada = ActualizarProductoInput(nombre="Laptop HP")

    with pytest.raises(ProductoNoEncontradoError):
        await service.ejecutar("PROD-999", entrada, _actualizado_por())


async def test_update_parcial_no_toca_campos_ausentes(service):
    entrada = ActualizarProductoInput(precio_unitario=500.0)

    producto = await service.ejecutar("PROD-001", entrada, _actualizado_por())

    assert producto.nombre == "Laptop"
    assert producto.precio_unitario == 500.0
