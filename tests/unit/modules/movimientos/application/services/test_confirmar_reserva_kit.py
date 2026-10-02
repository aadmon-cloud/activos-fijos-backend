from datetime import UTC, datetime
from unittest.mock import ANY, AsyncMock

import pytest

from modules.movimientos.application.services.ajustador_de_stock import AjustadorDeStockService
from modules.movimientos.application.services.confirmar_reserva_kit import (
    ConfirmarReservaKitService,
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
        session_id="session-kit-1",
        items=items,
        datos_adicionales=datos_adicionales,
        creado_por=_audit_persona(),
    ).model_copy(update={"id": "reserva-kit-1"})


@pytest.fixture
def reserva_repository_mock():
    mock = AsyncMock()
    mock.eliminar.return_value = True
    return mock


@pytest.fixture
def movimiento_repository_mock():
    mock = AsyncMock()
    mock.crear.side_effect = lambda movimiento, uow=None: movimiento.model_copy(
        update={"id": "mov-kit-1"}
    )
    return mock


@pytest.fixture
def producto_repository_mock():
    mock = AsyncMock()
    mock.obtener_por_codigo.side_effect = lambda codigo: _producto(codigo, f"Producto {codigo}")
    mock.actualizar.side_effect = lambda producto, uow=None: producto
    return mock


@pytest.fixture
def ubicacion_repository_mock():
    mock = AsyncMock()
    mock.obtener.side_effect = lambda codigo, ubicacion: Ubicacion.crear(
        codigo, ubicacion, 50, _audit_persona()
    )
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
    return ConfirmarReservaKitService(
        reserva_repository_mock,
        movimiento_repository_mock,
        ajustador_de_stock,
        generador_secuencial_mock,
        fake_unit_of_work_factory,
    )


def _items_reserva():
    return [
        ItemReserva(producto_codigo="PROD-001", ubicacion="A10-1", cantidad=3),
        ItemReserva(producto_codigo="PROD-002", ubicacion="A10-2", cantidad=1),
    ]


async def test_crea_un_solo_movimiento_kit(service, movimiento_repository_mock):
    reserva = _reserva(_items_reserva(), {"kitNombre": "Mercado Básico", "cliente": "Cliente Y"})

    movimiento = await service.ejecutar(reserva, _audit_persona())

    assert movimiento_repository_mock.crear.call_count == 1
    assert movimiento.tipo == "salida"
    assert movimiento.modalidad == "kit"
    assert movimiento.cantidad == 1
    assert movimiento.kit_nombre == "Mercado Básico"
    assert movimiento.cliente_destino == "Cliente Y"
    assert movimiento.remision == "RM-001"
    assert movimiento.numero_cajas == 0
    assert len(movimiento.productos) == 2


async def test_kit_nombre_por_defecto_si_no_viene(service):
    reserva = _reserva(_items_reserva(), {})

    movimiento = await service.ejecutar(reserva, _audit_persona())

    assert movimiento.kit_nombre == "Kit"


async def test_descuenta_stock_de_cada_ubicacion(service, ubicacion_repository_mock):
    reserva = _reserva(_items_reserva(), {"kitNombre": "Kit X"})

    await service.ejecutar(reserva, _audit_persona())

    assert ubicacion_repository_mock.actualizar.call_count == 2
    actualizadas = {c.args[0].ubicacion: c.args[0].stock_fisico for c in ubicacion_repository_mock.actualizar.call_args_list}
    assert actualizadas["A10-1"] == 47  # 50 - 3
    assert actualizadas["A10-2"] == 49  # 50 - 1


async def test_producto_no_encontrado_lanza_error(service, producto_repository_mock):
    producto_repository_mock.obtener_por_codigo.side_effect = None
    producto_repository_mock.obtener_por_codigo.return_value = None
    reserva = _reserva(_items_reserva(), {"kitNombre": "Kit X"})

    with pytest.raises(ProductoNoEncontradoError):
        await service.ejecutar(reserva, _audit_persona())


async def test_ubicacion_no_encontrada_lanza_error(service, ubicacion_repository_mock):
    ubicacion_repository_mock.obtener.side_effect = None
    ubicacion_repository_mock.obtener.return_value = None
    reserva = _reserva(_items_reserva(), {"kitNombre": "Kit X"})

    with pytest.raises(MovimientoUbicacionNoEncontradaError):
        await service.ejecutar(reserva, _audit_persona())


async def test_stock_insuficiente_lanza_error(service, ubicacion_repository_mock):
    ubicacion_repository_mock.obtener.side_effect = None
    ubicacion_repository_mock.obtener.return_value = Ubicacion.crear(
        "PROD-001", "A10-1", 1, _audit_persona()
    )
    reserva = _reserva(_items_reserva(), {"kitNombre": "Kit X"})

    with pytest.raises(MovimientoStockInsuficienteError):
        await service.ejecutar(reserva, _audit_persona())


async def test_elimina_la_reserva_al_confirmar(service, reserva_repository_mock):
    reserva = _reserva(_items_reserva(), {"kitNombre": "Kit X"})

    await service.ejecutar(reserva, _audit_persona())

    reserva_repository_mock.eliminar.assert_called_once_with("session-kit-1", uow=ANY)
