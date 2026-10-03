from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.catalogos.application.services.obtener_condicion import ObtenerCondicionService
from modules.catalogos.domain.entities import Condicion
from modules.catalogos.domain.errors import CondicionNoEncontradaError
from shared.domain.entities.audit import AuditPersona


async def test_obtener_condicion_retorna_el_dto_si_existe():
    repositorio_mock = AsyncMock()
    repositorio_mock.obtener_por_id.return_value = Condicion(
        id="1",
        nombre="Bueno",
        color="#4CAF50",
        descripcion=None,
        creado_por=AuditPersona(id_persona="0", nombre="S", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )
    service = ObtenerCondicionService(repositorio_mock)

    resultado = await service.ejecutar("1")

    assert resultado.nombre == "Bueno"


async def test_obtener_condicion_lanza_error_si_no_existe():
    repositorio_mock = AsyncMock()
    repositorio_mock.obtener_por_id.return_value = None
    service = ObtenerCondicionService(repositorio_mock)

    with pytest.raises(CondicionNoEncontradaError):
        await service.ejecutar("1")
