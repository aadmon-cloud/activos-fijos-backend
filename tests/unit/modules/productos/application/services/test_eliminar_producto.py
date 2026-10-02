from unittest.mock import AsyncMock

import pytest

from modules.productos.application.services.eliminar_producto import EliminarProductoService
from modules.productos.domain.errors import ProductoNoEncontradoError


@pytest.fixture
def producto_repository_mock():
    mock = AsyncMock()
    mock.eliminar.return_value = True
    return mock


@pytest.fixture
def service(producto_repository_mock):
    return EliminarProductoService(producto_repository_mock)


async def test_elimina_producto_existente(service, producto_repository_mock):
    await service.ejecutar("PROD-001")
    producto_repository_mock.eliminar.assert_called_once_with("PROD-001")


async def test_producto_no_encontrado_lanza_error(service, producto_repository_mock):
    producto_repository_mock.eliminar.return_value = False

    with pytest.raises(ProductoNoEncontradoError):
        await service.ejecutar("PROD-999")
