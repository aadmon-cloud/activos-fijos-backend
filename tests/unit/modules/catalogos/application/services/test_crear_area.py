from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.catalogos.application.dto.crear_area_dto import CrearAreaDTO
from modules.catalogos.application.services.crear_area import CrearAreaService
from modules.catalogos.domain.entities import Area
from modules.catalogos.domain.errors import AreaNombreDuplicadoError
from shared.domain.entities.audit import AuditPersona


@pytest.fixture
def repositorio_mock():
    mock = AsyncMock()
    mock.obtener_por_nombre.return_value = None
    mock.guardar.side_effect = lambda area: Area(
        id="1",
        nombre=area.nombre,
        descripcion=area.descripcion,
        creado_por=area.creado_por,
        actualizado_por=area.actualizado_por,
    )
    return mock


async def test_crear_area_guarda_la_entidad_con_nombre_recortado(repositorio_mock):
    service = CrearAreaService(repositorio_mock)

    resultado = await service.ejecutar(
        CrearAreaDTO(nombre="  Direccion  ", creado_por_id="1", creado_por_nombre="Admin")
    )

    assert resultado.id == "1"
    assert resultado.nombre == "Direccion"
    repositorio_mock.guardar.assert_called_once()


async def test_crear_area_lanza_error_si_el_nombre_ya_existe(repositorio_mock):
    repositorio_mock.obtener_por_nombre.return_value = Area(
        id="9",
        nombre="Direccion",
        descripcion=None,
        creado_por=AuditPersona(id_persona="0", nombre="S", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )
    service = CrearAreaService(repositorio_mock)

    with pytest.raises(AreaNombreDuplicadoError):
        await service.ejecutar(
            CrearAreaDTO(nombre="Direccion", creado_por_id="1", creado_por_nombre="Admin")
        )

    repositorio_mock.guardar.assert_not_called()
