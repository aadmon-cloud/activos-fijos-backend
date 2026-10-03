from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.catalogos.application.services.eliminar_area import EliminarAreaService
from modules.catalogos.domain.entities import Area
from modules.catalogos.domain.errors import AreaEnUsoError, AreaNoEncontradaError
from shared.domain.entities.audit import AuditPersona


def _area() -> Area:
    return Area(
        id="1",
        nombre="Direccion",
        descripcion=None,
        creado_por=AuditPersona(id_persona="0", nombre="S", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )


@pytest.fixture
def repositorio_mock():
    mock = AsyncMock()
    mock.obtener_por_id.return_value = _area()
    return mock


@pytest.fixture
def verificador_uso_mock():
    mock = AsyncMock()
    mock.area_esta_en_uso.return_value = False
    return mock


async def test_eliminar_area_elimina_si_existe_y_no_esta_en_uso(
    repositorio_mock, verificador_uso_mock
):
    service = EliminarAreaService(repositorio_mock, verificador_uso_mock)

    await service.ejecutar("1")

    repositorio_mock.eliminar.assert_called_once_with("1")


async def test_eliminar_area_lanza_error_si_esta_en_uso(repositorio_mock, verificador_uso_mock):
    verificador_uso_mock.area_esta_en_uso.return_value = True
    service = EliminarAreaService(repositorio_mock, verificador_uso_mock)

    with pytest.raises(AreaEnUsoError):
        await service.ejecutar("1")

    repositorio_mock.eliminar.assert_not_called()


async def test_eliminar_area_lanza_error_si_no_existe(repositorio_mock, verificador_uso_mock):
    repositorio_mock.obtener_por_id.return_value = None
    service = EliminarAreaService(repositorio_mock, verificador_uso_mock)

    with pytest.raises(AreaNoEncontradaError):
        await service.ejecutar("1")

    repositorio_mock.eliminar.assert_not_called()
