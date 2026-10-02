from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.productos.application.dto.listar_productos import ListarProductosInput
from modules.productos.application.services.listar_productos import ListarProductosService
from modules.productos.domain.entities.producto import Producto
from shared.domain.entities.audit_persona import AuditPersona


def _producto(codigo: str):
    return Producto.crear(
        codigo=codigo,
        nombre=f"Producto {codigo}",
        descripcion=None,
        categoria=None,
        stock_minimo=0,
        precio_unitario=0.0,
        creado_por=AuditPersona(id_persona="user-id", nombre="admin", fecha=datetime.now(UTC)),
    )


@pytest.fixture
def producto_repository_mock():
    mock = AsyncMock()
    mock.listar_paginado.return_value = ([_producto("PROD-001"), _producto("PROD-002")], 2)
    return mock


@pytest.fixture
def service(producto_repository_mock):
    return ListarProductosService(producto_repository_mock)


async def test_lista_productos_paginados(service, producto_repository_mock):
    entrada = ListarProductosInput(pagina=1, limite=10)

    respuesta = await service.ejecutar(entrada)

    assert len(respuesta.resultado) == 2
    assert respuesta.total_elementos == 2
    assert respuesta.pagina_actual == 1
    producto_repository_mock.listar_paginado.assert_called_once_with(pagina=1, limite=10)
