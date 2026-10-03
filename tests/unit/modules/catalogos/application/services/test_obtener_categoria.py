from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.catalogos.application.services.obtener_categoria import ObtenerCategoriaService
from modules.catalogos.domain.entities import Categoria
from modules.catalogos.domain.errors import CategoriaNoEncontradaError
from shared.domain.entities.audit import AuditPersona


async def test_obtener_categoria_retorna_el_dto_si_existe():
    repositorio_mock = AsyncMock()
    repositorio_mock.obtener_por_id.return_value = Categoria(
        id="1",
        nombre="Muebles",
        descripcion=None,
        creado_por=AuditPersona(id_persona="0", nombre="S", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )
    service = ObtenerCategoriaService(repositorio_mock)

    resultado = await service.ejecutar("1")

    assert resultado.nombre == "Muebles"


async def test_obtener_categoria_lanza_error_si_no_existe():
    repositorio_mock = AsyncMock()
    repositorio_mock.obtener_por_id.return_value = None
    service = ObtenerCategoriaService(repositorio_mock)

    with pytest.raises(CategoriaNoEncontradaError):
        await service.ejecutar("1")
