from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.mercados_predefinidos.domain.entities.mercado_predefinido import (
    MercadoPredefinido,
    ProductoKit,
)
from modules.mercados_predefinidos.domain.errors import MercadoNoEncontradoError
from modules.movimientos.application.dto.registrar_salida_por_mercado import (
    ItemSalidaPorMercadoInput,
    RegistrarSalidaPorMercadoInput,
)
from modules.movimientos.application.services.ajustador_de_stock import AjustadorDeStockService
from modules.movimientos.application.services.registrar_salida_por_mercado import (
    RegistrarSalidaPorMercadoService,
)
from modules.movimientos.domain.errors import (
    MovimientoStockInsuficienteError,
    MovimientoUbicacionNoEncontradaError,
    MovimientoUbicacionNoEspecificadaError,
)
from modules.productos.domain.entities.producto import Producto
from modules.productos.domain.errors import ProductoNoEncontradoError
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


def _mercado():
    return MercadoPredefinido.crear(
        nombre="Mercado Básico",
        descripcion=None,
        productos=[
            ProductoKit(producto_id="PROD-001", cantidad=3, producto_nombre="Arroz"),
            ProductoKit(producto_id="PROD-002", cantidad=1, producto_nombre="Aceite"),
        ],
        creado_por=_audit_persona(),
    )


@pytest.fixture
def mercado_predefinido_repository_mock():
    mock = AsyncMock()
    mock.obtener_por_nombre.return_value = _mercado()
    return mock


@pytest.fixture
def movimiento_repository_mock():
    mock = AsyncMock()
    mock.crear.side_effect = lambda movimiento, uow=None: movimiento.model_copy(
        update={"id": "mov-mercado-1"}
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
    mercado_predefinido_repository_mock,
    movimiento_repository_mock,
    ajustador_de_stock,
    generador_secuencial_mock,
):
    return RegistrarSalidaPorMercadoService(
        mercado_predefinido_repository_mock,
        movimiento_repository_mock,
        ajustador_de_stock,
        generador_secuencial_mock,
        fake_unit_of_work_factory,
    )


def _entrada(cantidad=1, productos=None):
    return RegistrarSalidaPorMercadoInput(
        mercado_nombre="Mercado Básico",
        productos=productos
        if productos is not None
        else [
            ItemSalidaPorMercadoInput(producto_codigo="PROD-001", ubicacion="A10-1"),
            ItemSalidaPorMercadoInput(producto_codigo="PROD-002", ubicacion="A10-1"),
        ],
        cantidad=cantidad,
        cliente_destino="Cliente Y",
        notas=None,
        referencia="REF-1",
    )


async def test_crea_un_solo_movimiento_mercado(service, movimiento_repository_mock):
    movimiento = await service.ejecutar(_entrada(), _audit_persona())

    assert movimiento_repository_mock.crear.call_count == 1
    assert movimiento.tipo == "salida"
    assert movimiento.modalidad == "mercado"
    assert movimiento.nombre_mercado == "Mercado Básico"
    assert movimiento.motivo == "Salida de Mercado Básico"
    assert movimiento.cantidad == 1
    assert movimiento.referencia == "REF-1"
    assert movimiento.remision == "RM-001"
    assert len(movimiento.productos) == 2


async def test_multiplica_cantidades_por_la_cantidad_de_mercados(service):
    movimiento = await service.ejecutar(_entrada(cantidad=2), _audit_persona())

    cantidades = {item.producto_codigo: item.cantidad for item in movimiento.productos}
    assert cantidades["PROD-001"] == 6  # 3 * 2
    assert cantidades["PROD-002"] == 2  # 1 * 2
    assert movimiento.cantidad == 2


async def test_descuenta_stock_de_la_ubicacion_indicada(service, ubicacion_repository_mock):
    await service.ejecutar(_entrada(), _audit_persona())

    assert ubicacion_repository_mock.actualizar.call_count == 2
    actualizadas = {
        c.args[0].ubicacion: c.args[0].stock_fisico
        for c in ubicacion_repository_mock.actualizar.call_args_list
    }
    assert actualizadas["A10-1"] in (47, 49)  # 50-3 y 50-1, mismo nombre de ubicacion


async def test_mercado_no_encontrado_lanza_error(service, mercado_predefinido_repository_mock):
    mercado_predefinido_repository_mock.obtener_por_nombre.return_value = None

    with pytest.raises(MercadoNoEncontradoError):
        await service.ejecutar(_entrada(), _audit_persona())


async def test_producto_no_encontrado_lanza_error(service, producto_repository_mock):
    producto_repository_mock.obtener_por_codigo.side_effect = None
    producto_repository_mock.obtener_por_codigo.return_value = None

    with pytest.raises(ProductoNoEncontradoError):
        await service.ejecutar(_entrada(), _audit_persona())


async def test_ubicacion_no_encontrada_lanza_error(service, ubicacion_repository_mock):
    ubicacion_repository_mock.obtener.side_effect = None
    ubicacion_repository_mock.obtener.return_value = None

    with pytest.raises(MovimientoUbicacionNoEncontradaError):
        await service.ejecutar(_entrada(), _audit_persona())


async def test_stock_insuficiente_lanza_error(service, ubicacion_repository_mock):
    ubicacion_repository_mock.obtener.side_effect = None
    ubicacion_repository_mock.obtener.return_value = Ubicacion.crear(
        "PROD-001", "A10-1", 1, _audit_persona()
    )

    with pytest.raises(MovimientoStockInsuficienteError):
        await service.ejecutar(_entrada(), _audit_persona())


async def test_permite_ubicaciones_distintas_por_producto(service, ubicacion_repository_mock):
    """Caso real: cada producto del mercado vive en una ubicación física distinta
    (no hay una única ubicación válida para todo el mercado)."""
    entrada = _entrada(
        productos=[
            ItemSalidaPorMercadoInput(producto_codigo="PROD-001", ubicacion="ALMACEN_GENERAL"),
            ItemSalidaPorMercadoInput(producto_codigo="PROD-002", ubicacion="A10"),
        ]
    )

    movimiento = await service.ejecutar(entrada, _audit_persona())

    ubicaciones = {item.producto_codigo: item.ubicacion for item in movimiento.productos}
    assert ubicaciones == {"PROD-001": "ALMACEN_GENERAL", "PROD-002": "A10"}
    ubicaciones_consultadas = {c.args[1] for c in ubicacion_repository_mock.obtener.call_args_list}
    assert ubicaciones_consultadas == {"ALMACEN_GENERAL", "A10"}


async def test_producto_sin_ubicacion_especificada_lanza_error(service):
    entrada = _entrada(
        productos=[ItemSalidaPorMercadoInput(producto_codigo="PROD-001", ubicacion="A10-1")]
    )

    with pytest.raises(MovimientoUbicacionNoEspecificadaError):
        await service.ejecutar(entrada, _audit_persona())
