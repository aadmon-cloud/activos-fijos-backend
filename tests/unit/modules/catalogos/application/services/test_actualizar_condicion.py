from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.catalogos.application.dto.actualizar_condicion_dto import ActualizarCondicionDTO
from modules.catalogos.application.services.actualizar_condicion import (
    ActualizarCondicionService,
)
from modules.catalogos.domain.entities import Condicion
from modules.catalogos.domain.errors import (
    CondicionColorInvalidoError,
    CondicionNoEncontradaError,
    CondicionNombreDuplicadoError,
)
from shared.domain.entities.audit import AuditPersona


def _condicion(**overrides) -> Condicion:
    valores = dict(
        id="1",
        nombre="Bueno",
        color="#4CAF50",
        descripcion=None,
        creado_por=AuditPersona(id_persona="0", nombre="S", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )
    valores.update(overrides)
    return Condicion(**valores)


@pytest.fixture
def repositorio_mock():
    mock = AsyncMock()
    mock.obtener_por_id.return_value = _condicion()
    mock.obtener_por_nombre.return_value = None
    mock.guardar.side_effect = lambda condicion: condicion
    return mock


async def test_actualizar_condicion_cambia_el_color(repositorio_mock):
    service = ActualizarCondicionService(repositorio_mock)

    resultado = await service.ejecutar(
        ActualizarCondicionDTO(
            id_condicion="1",
            color="#000000",
            actualizado_por_id="9",
            actualizado_por_nombre="Admin",
        )
    )

    assert resultado.color == "#000000"


async def test_actualizar_condicion_lanza_error_si_el_color_no_es_valido(repositorio_mock):
    service = ActualizarCondicionService(repositorio_mock)

    with pytest.raises(CondicionColorInvalidoError):
        await service.ejecutar(
            ActualizarCondicionDTO(
                id_condicion="1",
                color="rojo",
                actualizado_por_id="9",
                actualizado_por_nombre="Admin",
            )
        )


async def test_actualizar_condicion_lanza_error_si_no_existe(repositorio_mock):
    repositorio_mock.obtener_por_id.return_value = None
    service = ActualizarCondicionService(repositorio_mock)

    with pytest.raises(CondicionNoEncontradaError):
        await service.ejecutar(
            ActualizarCondicionDTO(
                id_condicion="1", actualizado_por_id="9", actualizado_por_nombre="Admin"
            )
        )


async def test_actualizar_condicion_lanza_error_si_el_nuevo_nombre_ya_existe_en_otra_condicion(
    repositorio_mock,
):
    repositorio_mock.obtener_por_nombre.return_value = _condicion(id="2", nombre="Excelente")
    service = ActualizarCondicionService(repositorio_mock)

    with pytest.raises(CondicionNombreDuplicadoError):
        await service.ejecutar(
            ActualizarCondicionDTO(
                id_condicion="1",
                nombre="Excelente",
                actualizado_por_id="9",
                actualizado_por_nombre="Admin",
            )
        )
