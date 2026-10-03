from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.catalogos.application.dto.actualizar_categoria_dto import ActualizarCategoriaDTO
from modules.catalogos.application.services.actualizar_categoria import (
    ActualizarCategoriaService,
)
from modules.catalogos.domain.entities import Categoria
from modules.catalogos.domain.errors import (
    CategoriaNoEncontradaError,
    CategoriaNombreDuplicadaError,
)
from shared.domain.entities.audit import AuditPersona


def _categoria(**overrides) -> Categoria:
    valores = dict(
        id="1",
        nombre="Muebles",
        descripcion=None,
        creado_por=AuditPersona(id_persona="0", nombre="S", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )
    valores.update(overrides)
    return Categoria(**valores)


@pytest.fixture
def repositorio_mock():
    mock = AsyncMock()
    mock.obtener_por_id.return_value = _categoria()
    mock.obtener_por_nombre.return_value = None
    mock.guardar.side_effect = lambda categoria: categoria
    return mock


async def test_actualizar_categoria_cambia_el_nombre(repositorio_mock):
    service = ActualizarCategoriaService(repositorio_mock)

    resultado = await service.ejecutar(
        ActualizarCategoriaDTO(
            id_categoria="1",
            nombre="Mobiliario",
            actualizado_por_id="9",
            actualizado_por_nombre="Admin",
        )
    )

    assert resultado.nombre == "Mobiliario"


async def test_actualizar_categoria_lanza_error_si_no_existe(repositorio_mock):
    repositorio_mock.obtener_por_id.return_value = None
    service = ActualizarCategoriaService(repositorio_mock)

    with pytest.raises(CategoriaNoEncontradaError):
        await service.ejecutar(
            ActualizarCategoriaDTO(
                id_categoria="1", actualizado_por_id="9", actualizado_por_nombre="Admin"
            )
        )


async def test_actualizar_categoria_lanza_error_si_el_nuevo_nombre_ya_existe_en_otra_categoria(
    repositorio_mock,
):
    repositorio_mock.obtener_por_nombre.return_value = _categoria(id="2", nombre="Equipos")
    service = ActualizarCategoriaService(repositorio_mock)

    with pytest.raises(CategoriaNombreDuplicadaError):
        await service.ejecutar(
            ActualizarCategoriaDTO(
                id_categoria="1",
                nombre="Equipos",
                actualizado_por_id="9",
                actualizado_por_nombre="Admin",
            )
        )
