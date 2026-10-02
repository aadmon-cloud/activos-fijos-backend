from unittest.mock import AsyncMock

import pytest

from modules.movimientos.application.dto.exportar_movimientos_excel import (
    ExportarMovimientosExcelInput,
)
from modules.movimientos.application.services.exportar_movimientos_excel import (
    ExportarMovimientosExcelService,
)


@pytest.fixture
def movimiento_repository_mock():
    mock = AsyncMock()
    mock.listar_para_exportar.return_value = []
    return mock


@pytest.fixture
def service(movimiento_repository_mock):
    return ExportarMovimientosExcelService(movimiento_repository_mock)


async def test_delega_en_el_repositorio_sin_paginar(service, movimiento_repository_mock):
    entrada = ExportarMovimientosExcelInput(tipo="salida")

    await service.ejecutar(entrada)

    movimiento_repository_mock.listar_para_exportar.assert_called_once_with(entrada)
