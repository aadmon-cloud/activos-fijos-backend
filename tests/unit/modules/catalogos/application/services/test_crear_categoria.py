from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.catalogos.application.dto.crear_categoria_dto import CrearCategoriaDTO
from modules.catalogos.application.services.crear_categoria import CrearCategoriaService
from modules.catalogos.domain.entities import Categoria
from modules.catalogos.domain.errors import CategoriaNombreDuplicadaError
from shared.domain.entities.audit import AuditPersona


@pytest.fixture
def repositorio_mock():
    mock = AsyncMock()
    mock.obtener_por_nombre.return_value = None
    mock.guardar.side_effect = lambda categoria: Categoria(
        id="1",
        nombre=categoria.nombre,
        descripcion=categoria.descripcion,
        creado_por=categoria.creado_por,
        actualizado_por=categoria.actualizado_por,
    )
    return mock


async def test_crear_categoria_guarda_la_entidad_con_nombre_recortado(repositorio_mock):
    service = CrearCategoriaService(repositorio_mock)

    resultado = await service.ejecutar(
        CrearCategoriaDTO(nombre="  Muebles  ", creado_por_id="1", creado_por_nombre="Admin")
    )

    assert resultado.id == "1"
    assert resultado.nombre == "Muebles"


async def test_crear_categoria_lanza_error_si_el_nombre_ya_existe(repositorio_mock):
    repositorio_mock.obtener_por_nombre.return_value = Categoria(
        id="9",
        nombre="Muebles",
        descripcion=None,
        creado_por=AuditPersona(id_persona="0", nombre="S", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )
    service = CrearCategoriaService(repositorio_mock)

    with pytest.raises(CategoriaNombreDuplicadaError):
        await service.ejecutar(
            CrearCategoriaDTO(nombre="Muebles", creado_por_id="1", creado_por_nombre="Admin")
        )

    repositorio_mock.guardar.assert_not_called()
