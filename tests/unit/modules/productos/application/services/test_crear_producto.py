from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.productos.application.dto.crear_producto import CrearProductoInput
from modules.productos.application.services.crear_producto import CrearProductoService
from modules.productos.domain.errors import ProductoCodigoDuplicadoError
from shared.domain.entities.audit_persona import AuditPersona


def _creado_por():
    return AuditPersona(id_persona="user-id", nombre="admin", fecha=datetime.now(UTC))


@pytest.fixture
def producto_repository_mock():
    mock = AsyncMock()
    mock.existe_por_codigo.return_value = False
    mock.crear.side_effect = lambda producto: producto.model_copy(update={"id": "nuevo-id"})
    return mock


@pytest.fixture
def service(producto_repository_mock):
    return CrearProductoService(producto_repository_mock)


async def test_crea_producto_con_codigo_provisto(service, producto_repository_mock):
    entrada = CrearProductoInput(codigo="PROD-001", nombre="Laptop")

    producto = await service.ejecutar(entrada, _creado_por())

    assert producto.codigo == "PROD-001"
    assert producto.id == "nuevo-id"
    producto_repository_mock.existe_por_codigo.assert_called_once_with("PROD-001")


async def test_crea_producto_autogenera_codigo_si_no_se_provee(service):
    entrada = CrearProductoInput(nombre="Mouse")

    producto = await service.ejecutar(entrada, _creado_por())

    assert producto.codigo.startswith("PROD-")


async def test_codigo_duplicado_lanza_error(service, producto_repository_mock):
    producto_repository_mock.existe_por_codigo.return_value = True
    entrada = CrearProductoInput(codigo="PROD-001", nombre="Laptop")

    with pytest.raises(ProductoCodigoDuplicadoError):
        await service.ejecutar(entrada, _creado_por())


async def test_precio_y_stock_minimo_por_defecto(service):
    entrada = CrearProductoInput(nombre="Teclado")

    producto = await service.ejecutar(entrada, _creado_por())

    assert producto.precio_unitario == 0.0
    assert producto.stock_minimo == 0


async def test_acepta_precio_unitario_en_la_creacion(service):
    entrada = CrearProductoInput(nombre="Monitor", precio_unitario=250.5)

    producto = await service.ejecutar(entrada, _creado_por())

    assert producto.precio_unitario == 250.5
