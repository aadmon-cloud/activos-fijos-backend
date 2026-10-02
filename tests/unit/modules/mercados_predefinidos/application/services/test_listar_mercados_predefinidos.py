from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.mercados_predefinidos.application.services.listar_mercados_predefinidos import (
    ListarMercadosPredefinidosService,
)
from modules.mercados_predefinidos.domain.entities.mercado_predefinido import (
    MercadoPredefinido,
    ProductoKit,
)
from shared.domain.entities.audit_persona import AuditPersona


def _mercado(nombre: str):
    return MercadoPredefinido.crear(
        nombre=nombre,
        descripcion=None,
        productos=[ProductoKit(producto_id="100", cantidad=1, producto_nombre="ARROZ")],
        creado_por=AuditPersona(id_persona="admin-id", nombre="admin", fecha=datetime.now(UTC)),
    )


@pytest.fixture
def mercado_repository_mock():
    mock = AsyncMock()
    mock.listar.return_value = [_mercado("KIT_BASICO"), _mercado("KIT_GRANDE")]
    return mock


@pytest.fixture
def service(mercado_repository_mock):
    return ListarMercadosPredefinidosService(mercado_repository_mock)


async def test_lista_mercados_activos_por_defecto(service, mercado_repository_mock):
    mercados = await service.ejecutar()

    assert len(mercados) == 2
    mercado_repository_mock.listar.assert_called_once_with(True)


async def test_lista_todos_cuando_solo_activos_es_false(service, mercado_repository_mock):
    await service.ejecutar(solo_activos=False)

    mercado_repository_mock.listar.assert_called_once_with(False)
