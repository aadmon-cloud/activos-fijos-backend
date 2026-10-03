from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.catalogos.application.services.eliminar_sede import EliminarSedeService
from modules.catalogos.domain.entities import Sede
from modules.catalogos.domain.errors import SedeEnUsoError, SedeNoEncontradaError
from shared.domain.entities.audit import AuditPersona


def _sede() -> Sede:
    return Sede(
        id="1",
        nombre="Prado",
        descripcion=None,
        creado_por=AuditPersona(id_persona="0", nombre="S", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )


@pytest.fixture
def sede_repository_mock():
    mock = AsyncMock()
    mock.obtener_por_id.return_value = _sede()
    return mock


@pytest.fixture
def lugar_repository_mock():
    mock = AsyncMock()
    mock.existe_alguno_con_sede.return_value = False
    return mock


async def test_eliminar_sede_elimina_si_no_tiene_lugares(sede_repository_mock, lugar_repository_mock):
    service = EliminarSedeService(sede_repository_mock, lugar_repository_mock)

    await service.ejecutar("1")

    sede_repository_mock.eliminar.assert_called_once_with("1")


async def test_eliminar_sede_lanza_error_si_tiene_lugares(sede_repository_mock, lugar_repository_mock):
    lugar_repository_mock.existe_alguno_con_sede.return_value = True
    service = EliminarSedeService(sede_repository_mock, lugar_repository_mock)

    with pytest.raises(SedeEnUsoError):
        await service.ejecutar("1")

    sede_repository_mock.eliminar.assert_not_called()


async def test_eliminar_sede_lanza_error_si_no_existe(sede_repository_mock, lugar_repository_mock):
    sede_repository_mock.obtener_por_id.return_value = None
    service = EliminarSedeService(sede_repository_mock, lugar_repository_mock)

    with pytest.raises(SedeNoEncontradaError):
        await service.ejecutar("1")
