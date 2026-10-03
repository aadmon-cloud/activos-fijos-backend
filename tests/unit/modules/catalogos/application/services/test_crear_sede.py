from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.catalogos.application.dto.crear_sede_dto import CrearSedeDTO
from modules.catalogos.application.services.crear_sede import CrearSedeService
from modules.catalogos.domain.entities import Sede
from modules.catalogos.domain.errors import SedeNombreDuplicadoError
from shared.domain.entities.audit import AuditPersona


@pytest.fixture
def repositorio_mock():
    mock = AsyncMock()
    mock.obtener_por_nombre.return_value = None
    mock.guardar.side_effect = lambda sede: Sede(
        id="1",
        nombre=sede.nombre,
        descripcion=sede.descripcion,
        creado_por=sede.creado_por,
        actualizado_por=sede.actualizado_por,
    )
    return mock


async def test_crear_sede_guarda_la_entidad_con_nombre_recortado(repositorio_mock):
    service = CrearSedeService(repositorio_mock)

    resultado = await service.ejecutar(
        CrearSedeDTO(nombre="  Prado  ", creado_por_id="1", creado_por_nombre="Admin")
    )

    assert resultado.id == "1"
    assert resultado.nombre == "Prado"


async def test_crear_sede_lanza_error_si_el_nombre_ya_existe(repositorio_mock):
    repositorio_mock.obtener_por_nombre.return_value = Sede(
        id="9",
        nombre="Prado",
        descripcion=None,
        creado_por=AuditPersona(id_persona="0", nombre="S", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )
    service = CrearSedeService(repositorio_mock)

    with pytest.raises(SedeNombreDuplicadoError):
        await service.ejecutar(
            CrearSedeDTO(nombre="Prado", creado_por_id="1", creado_por_nombre="Admin")
        )

    repositorio_mock.guardar.assert_not_called()
