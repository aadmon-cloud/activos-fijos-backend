from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.mercados_predefinidos.application.dto.actualizar_mercado_predefinido import (
    ActualizarMercadoPredefinidoInput,
)
from modules.mercados_predefinidos.application.dto.producto_kit import ProductoKitInput
from modules.mercados_predefinidos.application.services.actualizar_mercado_predefinido import (
    ActualizarMercadoPredefinidoService,
)
from modules.mercados_predefinidos.domain.entities.mercado_predefinido import (
    MercadoPredefinido,
    ProductoKit,
)
from modules.mercados_predefinidos.domain.errors import MercadoNoEncontradoError
from modules.productos.domain.entities.producto import Producto
from modules.productos.domain.errors import ProductoNoEncontradoError
from shared.domain.entities.audit_persona import AuditPersona


def _audit_persona():
    return AuditPersona(id_persona="admin-id", nombre="admin", fecha=datetime.now(UTC))


def _mercado():
    return MercadoPredefinido.crear(
        nombre="KIT_BASICO",
        descripcion="Original",
        productos=[ProductoKit(producto_id="100", cantidad=2, producto_nombre="ARROZ")],
        creado_por=_audit_persona(),
    )


def _producto(codigo: str, nombre: str):
    return Producto.crear(
        codigo=codigo,
        nombre=nombre,
        descripcion=None,
        categoria=None,
        stock_minimo=0,
        precio_unitario=0.0,
        creado_por=_audit_persona(),
    )


@pytest.fixture
def mercado_repository_mock():
    mock = AsyncMock()
    mock.obtener_por_nombre.return_value = _mercado()
    mock.actualizar.side_effect = lambda mercado: mercado
    return mock


@pytest.fixture
def producto_repository_mock():
    mock = AsyncMock()
    mock.obtener_por_codigo.side_effect = lambda codigo: _producto(codigo, f"Producto {codigo}")
    return mock


@pytest.fixture
def service(mercado_repository_mock, producto_repository_mock):
    return ActualizarMercadoPredefinidoService(mercado_repository_mock, producto_repository_mock)


async def test_actualiza_activo_sin_tocar_productos(service):
    entrada = ActualizarMercadoPredefinidoInput(activo=False)

    mercado = await service.ejecutar("KIT_BASICO", entrada, _audit_persona())

    assert mercado.activo is False
    assert mercado.productos[0].producto_id == "100"


async def test_actualiza_productos_resolviendo_nombres_en_vivo(service):
    entrada = ActualizarMercadoPredefinidoInput(
        productos=[ProductoKitInput(producto_id="200", cantidad=5)]
    )

    mercado = await service.ejecutar("KIT_BASICO", entrada, _audit_persona())

    assert mercado.productos == [
        ProductoKit(producto_id="200", cantidad=5, producto_nombre="Producto 200")
    ]


async def test_mercado_no_encontrado_lanza_error(service, mercado_repository_mock):
    mercado_repository_mock.obtener_por_nombre.return_value = None
    entrada = ActualizarMercadoPredefinidoInput(activo=False)

    with pytest.raises(MercadoNoEncontradoError):
        await service.ejecutar("NO-EXISTE", entrada, _audit_persona())


async def test_producto_inexistente_lanza_error(service, producto_repository_mock):
    producto_repository_mock.obtener_por_codigo.side_effect = None
    producto_repository_mock.obtener_por_codigo.return_value = None
    entrada = ActualizarMercadoPredefinidoInput(
        productos=[ProductoKitInput(producto_id="NO-EXISTE", cantidad=1)]
    )

    with pytest.raises(ProductoNoEncontradoError):
        await service.ejecutar("KIT_BASICO", entrada, _audit_persona())
