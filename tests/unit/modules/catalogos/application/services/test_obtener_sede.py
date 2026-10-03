from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.catalogos.application.services.obtener_sede import ObtenerSedeService
from modules.catalogos.domain.entities import Sede
from modules.catalogos.domain.errors import SedeNoEncontradaError
from shared.domain.entities.audit import AuditPersona


async def test_obtener_sede_retorna_el_dto_si_existe():
    repositorio_mock = AsyncMock()
    repositorio_mock.obtener_por_id.return_value = Sede(
        id="1",
        nombre="Prado",
        descripcion=None,
        creado_por=AuditPersona(id_persona="0", nombre="S", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )
    service = ObtenerSedeService(repositorio_mock)

    resultado = await service.ejecutar("1")

    assert resultado.nombre == "Prado"


async def test_obtener_sede_lanza_error_si_no_existe():
    repositorio_mock = AsyncMock()
    repositorio_mock.obtener_por_id.return_value = None
    service = ObtenerSedeService(repositorio_mock)

    with pytest.raises(SedeNoEncontradaError):
        await service.ejecutar("1")
