from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.productos.domain.entities.producto import Producto
from modules.productos.domain.errors import ProductoNoEncontradoError
from modules.ubicaciones.application.services.eliminar_ubicacion import EliminarUbicacionService
from modules.ubicaciones.domain.entities.ubicacion import Ubicacion
from modules.ubicaciones.domain.errors import UbicacionNoEncontradaError
from shared.domain.entities.audit_persona import AuditPersona
from tests.unit.modules.ubicaciones.application.services._fakes import (
    fake_unit_of_work_factory,
)


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
    ).model_copy(update={"id": "id-1"})


@pytest.fixture
def producto_repository_mock():
    mock = AsyncMock()
    mock.obtener_por_codigo.return_value = _producto()
    mock.actualizar.side_effect = lambda producto, uow=None: producto
    return mock


@pytest.fixture
def ubicacion_repository_mock():
    mock = AsyncMock()
    mock.obtener.return_value = Ubicacion.crear("PROD-001", "A10-1", 50, _audit_persona())
    mock.eliminar.return_value = True
    mock.listar_por_producto.return_value = []
    return mock


@pytest.fixture
def service(ubicacion_repository_mock, producto_repository_mock):
    return EliminarUbicacionService(
        ubicacion_repository_mock, producto_repository_mock, fake_unit_of_work_factory
    )


async def test_elimina_ubicacion(service, ubicacion_repository_mock):
    await service.ejecutar("PROD-001", "A10-1")
    ubicacion_repository_mock.eliminar.assert_called_once()


async def test_recalcula_stock_actual_tras_eliminar(
    service, ubicacion_repository_mock, producto_repository_mock
):
    ubicacion_repository_mock.listar_por_producto.return_value = [
        Ubicacion.crear("PROD-001", "A10-2", 30, _audit_persona()),
    ]

    await service.ejecutar("PROD-001", "A10-1")

    producto_actualizado = producto_repository_mock.actualizar.call_args.args[0]
    assert producto_actualizado.stock_actual == 30


async def test_ubicacion_no_encontrada_lanza_error(service, ubicacion_repository_mock):
    ubicacion_repository_mock.obtener.return_value = None

    with pytest.raises(UbicacionNoEncontradaError):
        await service.ejecutar("PROD-001", "NO-EXISTE")


async def test_producto_no_encontrado_lanza_error(service, producto_repository_mock):
    producto_repository_mock.obtener_por_codigo.return_value = None

    with pytest.raises(ProductoNoEncontradoError):
        await service.ejecutar("PROD-001", "A10-1")
