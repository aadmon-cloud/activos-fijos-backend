from unittest.mock import AsyncMock

import pytest

from modules.inventario_reportes.application.services.obtener_valor_total_inventario import (
    ObtenerValorTotalInventarioService,
)


@pytest.fixture
def producto_repository_mock():
    mock = AsyncMock()
    mock.calcular_valor_total.return_value = 999.5
    return mock


async def test_delega_directamente_en_el_repositorio(producto_repository_mock):
    service = ObtenerValorTotalInventarioService(producto_repository_mock)

    resultado = await service.ejecutar()

    assert resultado == 999.5
    producto_repository_mock.calcular_valor_total.assert_called_once_with()
