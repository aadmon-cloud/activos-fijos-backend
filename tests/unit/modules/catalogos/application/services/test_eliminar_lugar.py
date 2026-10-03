from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.catalogos.application.services.eliminar_lugar import EliminarLugarService
from modules.catalogos.domain.entities import Lugar, TipoLugar
from modules.catalogos.domain.errors import LugarEnUsoError, LugarNoEncontradoError
from shared.domain.entities.audit import AuditPersona


def _lugar() -> Lugar:
    return Lugar(
        id="1",
        nombre="Bodega",
        tipo=TipoLugar.BODEGA,
        sede_id="1",
        creado_por=AuditPersona(id_persona="0", nombre="S", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )


@pytest.fixture
def repositorio_mock():
    mock = AsyncMock()
    mock.obtener_por_id.return_value = _lugar()
    return mock


@pytest.fixture
def verificador_uso_mock():
    mock = AsyncMock()
    mock.lugar_esta_en_uso.return_value = False
    return mock


async def test_eliminar_lugar_elimina_si_existe_y_no_esta_en_uso(
    repositorio_mock, verificador_uso_mock
):
    service = EliminarLugarService(repositorio_mock, verificador_uso_mock)

    await service.ejecutar("1")

    repositorio_mock.eliminar.assert_called_once_with("1")


async def test_eliminar_lugar_lanza_error_si_esta_en_uso(repositorio_mock, verificador_uso_mock):
    verificador_uso_mock.lugar_esta_en_uso.return_value = True
    service = EliminarLugarService(repositorio_mock, verificador_uso_mock)

    with pytest.raises(LugarEnUsoError):
        await service.ejecutar("1")

    repositorio_mock.eliminar.assert_not_called()


async def test_eliminar_lugar_lanza_error_si_no_existe(repositorio_mock, verificador_uso_mock):
    repositorio_mock.obtener_por_id.return_value = None
    service = EliminarLugarService(repositorio_mock, verificador_uso_mock)

    with pytest.raises(LugarNoEncontradoError):
        await service.ejecutar("1")

    repositorio_mock.eliminar.assert_not_called()
