from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.mercados_predefinidos.application.dto.crear_mercado_predefinido import (
    CrearMercadoPredefinidoInput,
)
from modules.mercados_predefinidos.application.dto.producto_kit import ProductoKitInput
from modules.mercados_predefinidos.application.services.crear_mercado_predefinido import (
    CrearMercadoPredefinidoService,
)
from modules.mercados_predefinidos.domain.errors import MercadoNombreDuplicadoError
from modules.productos.domain.entities.producto import Producto
from modules.productos.domain.errors import ProductoNoEncontradoError
from shared.domain.entities.audit_persona import AuditPersona


def _audit_persona():
    return AuditPersona(id_persona="admin-id", nombre="admin", fecha=datetime.now(UTC))


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
    mock.existe_por_nombre.return_value = False
    mock.crear.side_effect = lambda mercado: mercado.model_copy(update={"id": "id-1"})
    return mock


@pytest.fixture
def producto_repository_mock():
    mock = AsyncMock()
    mock.obtener_por_codigo.side_effect = lambda codigo: _producto(codigo, f"Producto {codigo}")
    return mock


@pytest.fixture
def service(mercado_repository_mock, producto_repository_mock):
    return CrearMercadoPredefinidoService(mercado_repository_mock, producto_repository_mock)


async def test_crea_mercado_resolviendo_nombres_en_vivo(service):
    entrada = CrearMercadoPredefinidoInput(
        nombre="KIT_BASICO",
        productos=[ProductoKitInput(producto_id="100", cantidad=2)],
    )

    mercado = await service.ejecutar(entrada, _audit_persona())

    assert mercado.nombre == "KIT_BASICO"
    assert mercado.productos[0].producto_nombre == "Producto 100"


async def test_nombre_duplicado_lanza_error(service, mercado_repository_mock):
    mercado_repository_mock.existe_por_nombre.return_value = True
    entrada = CrearMercadoPredefinidoInput(
        nombre="KIT_BASICO", productos=[ProductoKitInput(producto_id="100", cantidad=1)]
    )

    with pytest.raises(MercadoNombreDuplicadoError):
        await service.ejecutar(entrada, _audit_persona())


async def test_producto_inexistente_lanza_error(service, producto_repository_mock):
    producto_repository_mock.obtener_por_codigo.side_effect = None
    producto_repository_mock.obtener_por_codigo.return_value = None
    entrada = CrearMercadoPredefinidoInput(
        nombre="KIT_BASICO", productos=[ProductoKitInput(producto_id="NO-EXISTE", cantidad=1)]
    )

    with pytest.raises(ProductoNoEncontradoError):
        await service.ejecutar(entrada, _audit_persona())
