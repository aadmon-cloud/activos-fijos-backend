from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.mercados_predefinidos.application.services.obtener_mercado_predefinido import (
    ObtenerMercadoPredefinidoService,
)
from modules.mercados_predefinidos.domain.entities.mercado_predefinido import (
    MercadoPredefinido,
    ProductoKit,
)
from modules.mercados_predefinidos.domain.errors import MercadoNoEncontradoError
from shared.domain.entities.audit_persona import AuditPersona


def _mercado():
    return MercadoPredefinido.crear(
        nombre="KIT_BASICO",
        descripcion=None,
        productos=[ProductoKit(producto_id="100", cantidad=1, producto_nombre="ARROZ")],
        creado_por=AuditPersona(id_persona="admin-id", nombre="admin", fecha=datetime.now(UTC)),
    )


@pytest.fixture
def mercado_repository_mock():
    mock = AsyncMock()
    mock.obtener_por_nombre.return_value = _mercado()
    return mock


@pytest.fixture
def service(mercado_repository_mock):
    return ObtenerMercadoPredefinidoService(mercado_repository_mock)


async def test_obtiene_mercado_existente(service):
    mercado = await service.ejecutar("KIT_BASICO")
    assert mercado.nombre == "KIT_BASICO"


async def test_mercado_no_encontrado_lanza_error(service, mercado_repository_mock):
    mercado_repository_mock.obtener_por_nombre.return_value = None

    with pytest.raises(MercadoNoEncontradoError):
        await service.ejecutar("NO-EXISTE")
