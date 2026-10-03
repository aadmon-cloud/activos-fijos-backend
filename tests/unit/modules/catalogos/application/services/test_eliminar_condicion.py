from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.catalogos.application.services.eliminar_condicion import EliminarCondicionService
from modules.catalogos.domain.entities import Condicion
from modules.catalogos.domain.errors import CondicionEnUsoError, CondicionNoEncontradaError
from shared.domain.entities.audit import AuditPersona


def _condicion() -> Condicion:
    return Condicion(
        id="1",
        nombre="Bueno",
        color="#4CAF50",
        descripcion=None,
        creado_por=AuditPersona(id_persona="0", nombre="S", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )


@pytest.fixture
def repositorio_mock():
    mock = AsyncMock()
    mock.obtener_por_id.return_value = _condicion()
    return mock


@pytest.fixture
def verificador_uso_mock():
    mock = AsyncMock()
    mock.condicion_esta_en_uso.return_value = False
    return mock


async def test_eliminar_condicion_elimina_si_existe_y_no_esta_en_uso(
    repositorio_mock, verificador_uso_mock
):
    service = EliminarCondicionService(repositorio_mock, verificador_uso_mock)

    await service.ejecutar("1")

    repositorio_mock.eliminar.assert_called_once_with("1")


async def test_eliminar_condicion_lanza_error_si_esta_en_uso(
    repositorio_mock, verificador_uso_mock
):
    verificador_uso_mock.condicion_esta_en_uso.return_value = True
    service = EliminarCondicionService(repositorio_mock, verificador_uso_mock)

    with pytest.raises(CondicionEnUsoError):
        await service.ejecutar("1")

    repositorio_mock.eliminar.assert_not_called()


async def test_eliminar_condicion_lanza_error_si_no_existe(
    repositorio_mock, verificador_uso_mock
):
    repositorio_mock.obtener_por_id.return_value = None
    service = EliminarCondicionService(repositorio_mock, verificador_uso_mock)

    with pytest.raises(CondicionNoEncontradaError):
        await service.ejecutar("1")

    repositorio_mock.eliminar.assert_not_called()
