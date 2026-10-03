from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.catalogos.application.dto.crear_condicion_dto import CrearCondicionDTO
from modules.catalogos.application.services.crear_condicion import CrearCondicionService
from modules.catalogos.domain.entities import Condicion
from modules.catalogos.domain.errors import (
    CondicionColorInvalidoError,
    CondicionNombreDuplicadoError,
)
from shared.domain.entities.audit import AuditPersona


@pytest.fixture
def repositorio_mock():
    mock = AsyncMock()
    mock.obtener_por_nombre.return_value = None
    mock.guardar.side_effect = lambda condicion: Condicion(
        id="1",
        nombre=condicion.nombre,
        color=condicion.color,
        descripcion=condicion.descripcion,
        creado_por=condicion.creado_por,
        actualizado_por=condicion.actualizado_por,
    )
    return mock


async def test_crear_condicion_guarda_la_entidad(repositorio_mock):
    service = CrearCondicionService(repositorio_mock)

    resultado = await service.ejecutar(
        CrearCondicionDTO(
            nombre="Bueno", color="#4CAF50", creado_por_id="1", creado_por_nombre="Admin"
        )
    )

    assert resultado.id == "1"
    assert resultado.color == "#4CAF50"


async def test_crear_condicion_lanza_error_si_el_color_no_es_hexadecimal_valido(repositorio_mock):
    service = CrearCondicionService(repositorio_mock)

    with pytest.raises(CondicionColorInvalidoError):
        await service.ejecutar(
            CrearCondicionDTO(
                nombre="Bueno", color="rojo", creado_por_id="1", creado_por_nombre="Admin"
            )
        )

    repositorio_mock.guardar.assert_not_called()


async def test_crear_condicion_lanza_error_si_el_nombre_ya_existe(repositorio_mock):
    repositorio_mock.obtener_por_nombre.return_value = Condicion(
        id="9",
        nombre="Bueno",
        color="#4CAF50",
        descripcion=None,
        creado_por=AuditPersona(id_persona="0", nombre="S", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )
    service = CrearCondicionService(repositorio_mock)

    with pytest.raises(CondicionNombreDuplicadoError):
        await service.ejecutar(
            CrearCondicionDTO(
                nombre="Bueno", color="#4CAF50", creado_por_id="1", creado_por_nombre="Admin"
            )
        )
