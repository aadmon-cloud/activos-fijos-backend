from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.catalogos.application.services.obtener_lugar import ObtenerLugarService
from modules.catalogos.domain.entities import Lugar, TipoLugar
from modules.catalogos.domain.errors import LugarNoEncontradoError
from shared.domain.entities.audit import AuditPersona


async def test_obtener_lugar_retorna_el_dto_si_existe():
    repositorio_mock = AsyncMock()
    repositorio_mock.obtener_por_id.return_value = Lugar(
        id="1",
        nombre="Bodega",
        tipo=TipoLugar.BODEGA,
        sede_id="1",
        creado_por=AuditPersona(id_persona="0", nombre="S", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )
    service = ObtenerLugarService(repositorio_mock)

    resultado = await service.ejecutar("1")

    assert resultado.nombre == "Bodega"


async def test_obtener_lugar_lanza_error_si_no_existe():
    repositorio_mock = AsyncMock()
    repositorio_mock.obtener_por_id.return_value = None
    service = ObtenerLugarService(repositorio_mock)

    with pytest.raises(LugarNoEncontradoError):
        await service.ejecutar("1")
