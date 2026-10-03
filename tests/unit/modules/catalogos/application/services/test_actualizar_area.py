from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.catalogos.application.dto.actualizar_area_dto import ActualizarAreaDTO
from modules.catalogos.application.services.actualizar_area import ActualizarAreaService
from modules.catalogos.domain.entities import Area
from modules.catalogos.domain.errors import AreaNoEncontradaError, AreaNombreDuplicadoError
from shared.domain.entities.audit import AuditPersona


def _area(**overrides) -> Area:
    valores = dict(
        id="1",
        nombre="Direccion",
        descripcion=None,
        creado_por=AuditPersona(id_persona="0", nombre="S", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )
    valores.update(overrides)
    return Area(**valores)


@pytest.fixture
def repositorio_mock():
    mock = AsyncMock()
    mock.obtener_por_id.return_value = _area()
    mock.obtener_por_nombre.return_value = None
    mock.guardar.side_effect = lambda area: area
    return mock


async def test_actualizar_area_cambia_el_nombre(repositorio_mock):
    service = ActualizarAreaService(repositorio_mock)

    resultado = await service.ejecutar(
        ActualizarAreaDTO(
            id_area="1",
            nombre="Direccion General",
            actualizado_por_id="9",
            actualizado_por_nombre="Admin",
        )
    )

    assert resultado.nombre == "Direccion General"


async def test_actualizar_area_lanza_error_si_no_existe(repositorio_mock):
    repositorio_mock.obtener_por_id.return_value = None
    service = ActualizarAreaService(repositorio_mock)

    with pytest.raises(AreaNoEncontradaError):
        await service.ejecutar(
            ActualizarAreaDTO(id_area="1", actualizado_por_id="9", actualizado_por_nombre="Admin")
        )


async def test_actualizar_area_lanza_error_si_el_nuevo_nombre_ya_existe_en_otra_area(
    repositorio_mock,
):
    repositorio_mock.obtener_por_nombre.return_value = _area(id="2", nombre="Tecnologia")
    service = ActualizarAreaService(repositorio_mock)

    with pytest.raises(AreaNombreDuplicadoError):
        await service.ejecutar(
            ActualizarAreaDTO(
                id_area="1",
                nombre="Tecnologia",
                actualizado_por_id="9",
                actualizado_por_nombre="Admin",
            )
        )


async def test_actualizar_area_permite_conservar_el_mismo_nombre(repositorio_mock):
    repositorio_mock.obtener_por_nombre.return_value = _area()
    service = ActualizarAreaService(repositorio_mock)

    resultado = await service.ejecutar(
        ActualizarAreaDTO(
            id_area="1",
            nombre="Direccion",
            descripcion="Nueva descripcion",
            actualizado_por_id="9",
            actualizado_por_nombre="Admin",
        )
    )

    assert resultado.descripcion == "Nueva descripcion"
