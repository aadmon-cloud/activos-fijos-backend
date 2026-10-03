from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.catalogos.application.dto.actualizar_sede_dto import ActualizarSedeDTO
from modules.catalogos.application.services.actualizar_sede import ActualizarSedeService
from modules.catalogos.domain.entities import Sede
from modules.catalogos.domain.errors import SedeNoEncontradaError, SedeNombreDuplicadoError
from shared.domain.entities.audit import AuditPersona


def _sede(**overrides) -> Sede:
    valores = dict(
        id="1",
        nombre="Prado",
        descripcion=None,
        creado_por=AuditPersona(id_persona="0", nombre="S", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )
    valores.update(overrides)
    return Sede(**valores)


@pytest.fixture
def repositorio_mock():
    mock = AsyncMock()
    mock.obtener_por_id.return_value = _sede()
    mock.obtener_por_nombre.return_value = None
    mock.guardar.side_effect = lambda sede: sede
    return mock


async def test_actualizar_sede_cambia_el_nombre(repositorio_mock):
    service = ActualizarSedeService(repositorio_mock)

    resultado = await service.ejecutar(
        ActualizarSedeDTO(
            id_sede="1", nombre="Prado Norte", actualizado_por_id="9", actualizado_por_nombre="Admin"
        )
    )

    assert resultado.nombre == "Prado Norte"


async def test_actualizar_sede_lanza_error_si_no_existe(repositorio_mock):
    repositorio_mock.obtener_por_id.return_value = None
    service = ActualizarSedeService(repositorio_mock)

    with pytest.raises(SedeNoEncontradaError):
        await service.ejecutar(
            ActualizarSedeDTO(id_sede="1", actualizado_por_id="9", actualizado_por_nombre="Admin")
        )


async def test_actualizar_sede_lanza_error_si_el_nuevo_nombre_ya_existe_en_otra_sede(
    repositorio_mock,
):
    repositorio_mock.obtener_por_nombre.return_value = _sede(id="2", nombre="Bosa")
    service = ActualizarSedeService(repositorio_mock)

    with pytest.raises(SedeNombreDuplicadoError):
        await service.ejecutar(
            ActualizarSedeDTO(
                id_sede="1", nombre="Bosa", actualizado_por_id="9", actualizado_por_nombre="Admin"
            )
        )
