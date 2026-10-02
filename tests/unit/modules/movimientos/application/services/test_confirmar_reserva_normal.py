from datetime import UTC, datetime
from unittest.mock import ANY, AsyncMock

import pytest

from modules.movimientos.application.services.ajustador_de_stock import AjustadorDeStockService
from modules.movimientos.application.services.confirmar_reserva_normal import (
    ConfirmarReservaNormalService,
)
from modules.movimientos.domain.errors import (
    MovimientoStockInsuficienteError,
    MovimientoUbicacionNoEncontradaError,
)
from modules.productos.domain.entities.producto import Producto
from modules.productos.domain.errors import ProductoNoEncontradoError
from modules.reservas.domain.entities.reserva import ItemReserva, Reserva
from modules.ubicaciones.domain.entities.ubicacion import Ubicacion
from shared.domain.entities.audit_persona import AuditPersona
from tests.unit.modules.movimientos.application.services._fakes import (
    fake_unit_of_work_factory,
)


def _audit_persona():
    return AuditPersona(id_persona="admin-id", nombre="admin", fecha=datetime.now(UTC))


def _producto(codigo="PROD-001", nombre="Arroz"):
    return Producto.crear(
        codigo=codigo,
        nombre=nombre,
        descripcion=None,
        categoria=None,
        stock_minimo=0,
        precio_unitario=0.0,
        creado_por=_audit_persona(),
    ).model_copy(update={"id": f"id-{codigo}"})


def _reserva(items, datos_adicionales=None):
    return Reserva.crear(
        session_id="session-1",
        items=items,
        datos_adicionales=datos_adicionales,
        creado_por=_audit_persona(),
    ).model_copy(update={"id": "reserva-1"})


@pytest.fixture
def reserva_repository_mock():
    mock = AsyncMock()
    mock.eliminar.return_value = True
    return mock


@pytest.fixture
def movimiento_repository_mock():
    mock = AsyncMock()
    mock.crear.side_effect = lambda movimiento, uow=None: movimiento.model_copy(
        update={"id": f"mov-{movimiento.producto_codigo}"}
    )
    return mock


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
    mock.actualizar.side_effect = lambda ubicacion, uow=None: ubicacion
    mock.listar_por_producto.return_value = []
    return mock


@pytest.fixture
def generador_secuencial_mock():
    mock = AsyncMock()
    mock.siguiente.return_value = "RM-001"
    return mock


@pytest.fixture
def ajustador_de_stock(producto_repository_mock, ubicacion_repository_mock):
    return AjustadorDeStockService(producto_repository_mock, ubicacion_repository_mock)


@pytest.fixture
def service(
    reserva_repository_mock,
    movimiento_repository_mock,
    ajustador_de_stock,
    generador_secuencial_mock,
):
    return ConfirmarReservaNormalService(
        reserva_repository_mock,
        movimiento_repository_mock,
        ajustador_de_stock,
        generador_secuencial_mock,
        fake_unit_of_work_factory,
    )


async def test_producto_no_encontrado_lanza_error(service, producto_repository_mock):
    producto_repository_mock.obtener_por_codigo.return_value = None
    reserva = _reserva([ItemReserva(producto_codigo="PROD-001", ubicacion="A10-1", cantidad=5)])

    with pytest.raises(ProductoNoEncontradoError):
        await service.ejecutar(reserva, _audit_persona())


async def test_ubicacion_no_encontrada_lanza_error(service, ubicacion_repository_mock):
    ubicacion_repository_mock.obtener.return_value = None
    reserva = _reserva([ItemReserva(producto_codigo="PROD-001", ubicacion="A10-1", cantidad=5)])

    with pytest.raises(MovimientoUbicacionNoEncontradaError):
        await service.ejecutar(reserva, _audit_persona())


async def test_stock_insuficiente_lanza_error(service, ubicacion_repository_mock):
    ubicacion_repository_mock.obtener.return_value = Ubicacion.crear(
        "PROD-001", "A10-1", 1, _audit_persona()
    )
    reserva = _reserva([ItemReserva(producto_codigo="PROD-001", ubicacion="A10-1", cantidad=5)])

    with pytest.raises(MovimientoStockInsuficienteError):
        await service.ejecutar(reserva, _audit_persona())


async def test_descuenta_stock_una_sola_vez(service, ubicacion_repository_mock):
    reserva = _reserva([ItemReserva(producto_codigo="PROD-001", ubicacion="A10-1", cantidad=5)])

    await service.ejecutar(reserva, _audit_persona())

    ubicacion_repository_mock.actualizar.assert_called_once()
    actualizada = ubicacion_repository_mock.actualizar.call_args.args[0]
    assert actualizada.stock_fisico == 45  # 50 - 5, una sola vez (corrige el bug del legacy)


async def test_crea_un_movimiento_por_item_con_remision_compartida(
    service, movimiento_repository_mock
):
    reserva = _reserva(
        [
            ItemReserva(producto_codigo="PROD-001", ubicacion="A10-1", cantidad=5),
            ItemReserva(producto_codigo="PROD-001", ubicacion="A10-2", cantidad=3),
        ],
        {"cliente": "Cliente Y"},
    )

    movimientos = await service.ejecutar(reserva, _audit_persona())

    assert len(movimientos) == 2
    assert all(m.remision == "RM-001" for m in movimientos)
    assert all(m.tipo == "salida" for m in movimientos)
    assert all(m.cliente_destino == "Cliente Y" for m in movimientos)
    assert movimiento_repository_mock.crear.call_count == 2


async def test_elimina_la_reserva_al_confirmar(service, reserva_repository_mock):
    reserva = _reserva([ItemReserva(producto_codigo="PROD-001", ubicacion="A10-1", cantidad=5)])

    await service.ejecutar(reserva, _audit_persona())

    reserva_repository_mock.eliminar.assert_called_once_with("session-1", uow=ANY)


async def test_no_elimina_la_reserva_si_falla_un_item(
    service, reserva_repository_mock, ubicacion_repository_mock
):
    ubicacion_repository_mock.obtener.return_value = None
    reserva = _reserva([ItemReserva(producto_codigo="PROD-001", ubicacion="A10-1", cantidad=5)])

    with pytest.raises(MovimientoUbicacionNoEncontradaError):
        await service.ejecutar(reserva, _audit_persona())

    reserva_repository_mock.eliminar.assert_not_called()
