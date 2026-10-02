from datetime import UTC, datetime
from unittest.mock import ANY, AsyncMock

import pytest

from modules.productos.domain.entities.producto import Producto
from modules.productos.domain.errors import ProductoNoEncontradoError
from modules.ubicaciones.application.dto.crear_ubicacion import CrearUbicacionInput
from modules.ubicaciones.application.services.crear_ubicacion import CrearUbicacionService
from modules.ubicaciones.domain.entities.ubicacion import Ubicacion
from modules.ubicaciones.domain.errors import UbicacionDuplicadaError
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
    mock.existe.return_value = False
    mock.crear.side_effect = lambda ubicacion, uow=None: ubicacion.model_copy(
        update={"id": "ubic-id"}
    )
    mock.listar_por_producto.return_value = []
    return mock


@pytest.fixture
def registrador_de_movimientos_mock():
    return AsyncMock()


@pytest.fixture
def service(ubicacion_repository_mock, producto_repository_mock, registrador_de_movimientos_mock):
    return CrearUbicacionService(
        ubicacion_repository_mock,
        producto_repository_mock,
        registrador_de_movimientos_mock,
        fake_unit_of_work_factory,
    )


async def test_crea_ubicacion(service, ubicacion_repository_mock):
    entrada = CrearUbicacionInput(producto_codigo="PROD-001", ubicacion="A10-1", cantidad=50)

    ubicacion = await service.ejecutar(entrada, _audit_persona())

    assert ubicacion.producto_codigo == "PROD-001"
    assert ubicacion.ubicacion == "A10-1"
    assert ubicacion.stock_fisico == 50
    ubicacion_repository_mock.existe.assert_called_once_with("PROD-001", "A10-1")


async def test_recalcula_stock_actual_como_suma_de_ubicaciones(
    service, ubicacion_repository_mock, producto_repository_mock
):
    ubicacion_repository_mock.listar_por_producto.return_value = [
        Ubicacion.crear("PROD-001", "A10-1", 50, _audit_persona()),
        Ubicacion.crear("PROD-001", "A10-2", 30, _audit_persona()),
    ]
    entrada = CrearUbicacionInput(producto_codigo="PROD-001", ubicacion="A10-3", cantidad=20)

    await service.ejecutar(entrada, _audit_persona())

    producto_actualizado = producto_repository_mock.actualizar.call_args.args[0]
    assert producto_actualizado.stock_actual == 80


async def test_producto_no_encontrado_lanza_error(service, producto_repository_mock):
    producto_repository_mock.obtener_por_codigo.return_value = None
    entrada = CrearUbicacionInput(producto_codigo="NO-EXISTE", ubicacion="A10-1")

    with pytest.raises(ProductoNoEncontradoError):
        await service.ejecutar(entrada, _audit_persona())


async def test_ubicacion_duplicada_lanza_error(service, ubicacion_repository_mock):
    ubicacion_repository_mock.existe.return_value = True
    entrada = CrearUbicacionInput(producto_codigo="PROD-001", ubicacion="A10-1")

    with pytest.raises(UbicacionDuplicadaError):
        await service.ejecutar(entrada, _audit_persona())


async def test_registra_bitacora_de_movimientos(service, registrador_de_movimientos_mock):
    entrada = CrearUbicacionInput(producto_codigo="PROD-001", ubicacion="A10-1", cantidad=50)
    creado_por = _audit_persona()

    await service.ejecutar(entrada, creado_por)

    registrador_de_movimientos_mock.registrar_creacion_ubicacion.assert_called_once_with(
        producto_codigo="PROD-001",
        ubicacion="A10-1",
        cantidad=50,
        creado_por=creado_por,
        uow=ANY,
    )
