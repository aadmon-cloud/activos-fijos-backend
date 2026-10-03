from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.catalogos.application.dto.actualizar_lugar_dto import ActualizarLugarDTO
from modules.catalogos.application.services.actualizar_lugar import ActualizarLugarService
from modules.catalogos.domain.entities import Lugar, TipoLugar
from modules.catalogos.domain.errors import LugarNoEncontradoError, LugarNombreDuplicadoError
from shared.domain.entities.audit import AuditPersona


def _lugar(**overrides) -> Lugar:
    valores = dict(
        id="1",
        nombre="Bodega",
        tipo=TipoLugar.BODEGA,
        sede_id="1",
        creado_por=AuditPersona(id_persona="0", nombre="S", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )
    valores.update(overrides)
    return Lugar(**valores)


@pytest.fixture
def repositorio_mock():
    mock = AsyncMock()
    mock.obtener_por_id.return_value = _lugar()
    mock.obtener_por_nombre_y_sede.return_value = None
    mock.guardar.side_effect = lambda lugar: lugar
    return mock


async def test_actualizar_lugar_cambia_el_tipo(repositorio_mock):
    service = ActualizarLugarService(repositorio_mock)

    resultado = await service.ejecutar(
        ActualizarLugarDTO(
            id_lugar="1",
            tipo=TipoLugar.ESPACIO_COMUN,
            actualizado_por_id="9",
            actualizado_por_nombre="Admin",
        )
    )

    assert resultado.tipo == "espacio_comun"


async def test_actualizar_lugar_lanza_error_si_no_existe(repositorio_mock):
    repositorio_mock.obtener_por_id.return_value = None
    service = ActualizarLugarService(repositorio_mock)

    with pytest.raises(LugarNoEncontradoError):
        await service.ejecutar(
            ActualizarLugarDTO(id_lugar="1", actualizado_por_id="9", actualizado_por_nombre="Admin")
        )


async def test_actualizar_lugar_lanza_error_si_el_nuevo_nombre_ya_existe_en_la_misma_sede(
    repositorio_mock,
):
    repositorio_mock.obtener_por_nombre_y_sede.return_value = _lugar(id="2", nombre="Bano")
    service = ActualizarLugarService(repositorio_mock)

    with pytest.raises(LugarNombreDuplicadoError):
        await service.ejecutar(
            ActualizarLugarDTO(
                id_lugar="1", nombre="Bano", actualizado_por_id="9", actualizado_por_nombre="Admin"
            )
        )
