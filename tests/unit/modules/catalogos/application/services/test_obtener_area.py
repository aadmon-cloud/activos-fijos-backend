from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.catalogos.application.services.obtener_area import ObtenerAreaService
from modules.catalogos.domain.entities import Area
from modules.catalogos.domain.errors import AreaNoEncontradaError
from shared.domain.entities.audit import AuditPersona


async def test_obtener_area_retorna_el_dto_si_existe():
    repositorio_mock = AsyncMock()
    repositorio_mock.obtener_por_id.return_value = Area(
        id="1",
        nombre="Direccion",
        descripcion=None,
        creado_por=AuditPersona(id_persona="0", nombre="S", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )
    service = ObtenerAreaService(repositorio_mock)

    resultado = await service.ejecutar("1")

    assert resultado.nombre == "Direccion"


async def test_obtener_area_lanza_error_si_no_existe():
    repositorio_mock = AsyncMock()
    repositorio_mock.obtener_por_id.return_value = None
    service = ObtenerAreaService(repositorio_mock)

    with pytest.raises(AreaNoEncontradaError):
        await service.ejecutar("1")
